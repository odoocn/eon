from openerp import _, models, fields, api
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import time


class eon_sale_order(models.Model):

    _name = 'eon.sale.order'

    name = fields.Char(string='Sale Order')
    partner_id = fields.Many2one('res.partner', 'Customer Name', required=True)
    date_order = fields.Datetime(string="Date")
    sales_person_id = fields.Many2one('res.users','Sales Person',required=True)
    balance = fields.Float(string="Balance")
    sub_total = fields.Float(string="Sub Total")
    amount_tax = fields.Float(string="Tax")
    invoice_number = fields.Char(string="Invoice Number")
    invoice_date = fields.Date(string="Invoice Date")
    order_state = fields.Selection([('draft', 'Draft Quotation'),
                                    ('sent', 'Quotation Sent'),
                                    ('cancel', 'Cancelled'),
                                    ('waiting_date', 'Waiting Schedule'),
                                    ('progress', 'Sales Order'),
                                    ('manual', 'Sale to Invoice'),
                                    ('shipping_except', 'Shipping Exception'),
                                    ('invoice_except', 'Invoice Exception'),
                                    ('done', 'Done'),
                                    ], 'Sale Order Status', readonly=True, copy=False,)
    invoice_state = fields.Selection([('draft', 'Draft'),
                                    ('proforma', 'Pro-forma'),
                                    ('proforma2', 'Pro-forma'),
                                    ('open', 'Open'), ('paid', 'Paid'),
                                    ('partial', 'Partial'),
                                    ('cancel', 'Cancelled')
                                    ], string=' Invoice Status', index=True, readonly=True, default='draft')
    picking_state = fields.Selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),
                                   ('confirmed', 'Waiting Availability'),
                                   ('assigned', 'Ready To Transfer'),
                                   ('partialy_availible', 'Partial Available'),
                                   ('done', 'Done')
                                   ], 'Picking Status', readonly=True, select=True, copy=False)
    partner_invoice_id = fields.Many2one('res.partner', 'Partner Address',required=True)
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address' ,required=True)
    move_ids = fields.One2many('eon.stock.move.line','sale_order_id', 'Stock Move')
    invoice_lines = fields.One2many('eon.invoice.line', 'sale_order_id', string="Invoice Line")
    picking_number = fields.Char(string="Picking Number")
    picking_date = fields.Date(string="Picking Date")
    client_order_ref = fields.Char(string='Reference/Description')
    due_date = fields.Date(string="Due Date")
    invoice_total = fields.Float(string="Total")
    backorder_id = fields.Many2one('stock.picking','Back Order')


class eon_stock_move_line(models.Model):
    _name = 'eon.stock.move.line'

    sale_order_id = fields.Many2one('eon.sale.order', string='Sale Order')
    product_id = fields.Many2one('product.product', 'Product', required='True')
    uom_id = fields.Many2one('product.uom', 'Product Unit of Measure', required='True')
    unit_price = fields.Float('Unit Price')
    qty = fields.Float('Quantity')
    state = fields.Selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),
                                   ('confirmed', 'Waiting Availability'),
                                   ('assigned', 'Available'),
                                   ('done', 'Done'),
                                   ], 'Status', readonly=True, select=True, copy=False)
    source_location_id = fields.Many2one('stock.location','Source Location')
    destination_location_id = fields.Many2one('stock.location','Destination Location')

class eon_invoice_line(models.Model):
    _name = 'eon.invoice.line'

    sale_order_id = fields.Many2one('eon.sale.order', string='Sale Order')
    product_id = fields.Many2one('product.product', 'Product', required='True')
    name = fields.Char('Description')
    uom_id = fields.Many2one('product.uom', 'Unit of Measure', required='True')
    account_id = fields.Many2one('account.account', 'Account')
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    qty = fields.Float('Quantity')
    unit_price = fields.Float('Unit Price')
    discount = fields.Float('Discount')
    invoice_line_tax_ids = fields.Many2many('account.tax','rel_tbl_account_invoice_taxt','rel_invoice_line','rel_account_tax_id','Taxes')
    price_subtotal = fields.Float('Sub Total')

class sale_order(models.Model):
    _inherit = 'sale.order'

    sale_order_id = fields.Many2one('eon.sale.order','Sale Order')

    @api.cr_uid_context
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sales order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        res_invoice_vals = super(sale_order, self)._prepare_invoice(cr, uid, order=order, lines=lines, context=context)
        res_invoice_vals.update({'sale_id': order.id})
        return res_invoice_vals

    @api.cr_uid_context
    def _make_invoice(self, cr, uid, order, lines, context=None):
        inv_id = super(sale_order, self)._make_invoice(cr, uid, order=order, lines=lines, context=context)
        eon_account_obj = self.pool.get('eon.sale.order')
        invoice_line_obj = self.pool.get('eon.invoice.line')
        vals = {}
        for invoice in self.pool.get('account.invoice').browse(cr, uid, inv_id, context=context):
            for invoice_lines in invoice.invoice_line:
                vals.update({
                    'product_id': invoice_lines.product_id.id or False,
                    'name': invoice_lines.name or '',
                    'qty': invoice_lines.quantity or '',
                    'uom_id': invoice_lines.uos_id.id or False,
                    'account_id': invoice_lines.account_id.id or False,
                    'account_analytic_id': invoice_lines.account_analytic_id.id or False,
                    'discount': invoice_lines.discount or '',
                    'invoice_line_tax_ids': [(6, 0, [x.id for x in invoice_lines.invoice_line_tax_id])] or False,
                    'price_subtotal': invoice_lines.price_subtotal or False,
                    'sale_order_id': order.sale_order_id.id or False
                })
                inv_line_rec_id = invoice_line_obj.create(cr, uid, vals, context=context)
                if order.sale_order_id.id:
                    eon_account_obj.write(cr, uid,order.sale_order_id.id ,{'sub_total': invoice.amount_untaxed or 0.0,'amount_tax': invoice.amount_tax or 0.0,'invoice_total': invoice.amount_total or 0.0,'balance': invoice.residual or 0.0,'invoice_state': invoice.state})
        return inv_id

    @api.multi
    def action_button_confirm(self):
        print "\n\n\n::::::::::::,self....",self
        res = super(sale_order, self).action_button_confirm()
        if self.id:
            vals = {}
            mv_line_lst = []
            picking_dt = ''
            picking_no = ''
            for picking in self.picking_ids:
                for move_line in picking.move_lines:
                    vals.update({
                        'product_id' : move_line.product_id.id,
                        'qty': move_line.product_uom_qty,
                        'uom_id': move_line.product_uom.id,
                        'state': move_line.state,
                        'source_location_id': move_line.location_id.id,
                        'destination_location_id': move_line.location_dest_id.id,
                        'sale_order_id': self.sale_order_id.id
                    })
                    print "\n\nUpdate:::::valsssss:::",vals
                    rec_id = self.env['eon.stock.move.line'].create(vals)
                    print "\n\nMove Id::::ffrrr::rrrr::r::::",rec_id
                picking_dt = picking.date or ''
                picking_no = picking.name or ''
                print "Currebnnnnt dt::::::",picking_dt
                print "\n\npicking_no::::::::::::",picking_no
            if picking_dt:
                picking_date =  datetime.strptime(picking_dt, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y/%m/%d')
                print "\n\npicking_date::::::::::::::::::::::::",picking_date
            res = self.sale_order_id.write({'order_state': 'progress','picking_date': picking_date,'picking_number': picking_no})
            print "\n\nrec_id::::::::::::::::",res 
        return res

    @api.multi
    def action_cancel(self):
        res = super(sale_order, self).action_cancel()
        eon_account_obj = self.env['eon.sale.order']
        for rec in self:
            rec = eon_account_obj.browse(rec.sale_order_id.id).write({'order_state': 'cancel','picking_state': 'cancel'})
        return res

    @api.multi
    def action_ignore_delivery_exception(self):
        res = super(sale_order, self).action_ignore_delivery_exception()
        for sale in self.browse(self.ids):
            res = self.write({'state': 'progress' if sale.invoice_exists else 'manual'})
        if self.sale_order_id:
            rec = self.sale_order_id.write({'order_state': 'progress'})
        return res

    @api.model
    def create(self, vals):
        res_vals = super(sale_order, self).create(vals)
        rec_vals = {}
        rec_vals.update({'name': vals.get('name',False),'partner_id': vals.get('partner_id',False),
                   'partner_invoice_id': vals.get('partner_invoice_id',False),
                   'partner_shipping_id': vals.get('partner_shipping_id',False),
                   'date_order': vals.get('date_order',False),'client_order_ref': vals.get('client_order_ref', False),
                   'sales_person_id': vals.get('user_id', False),'order_state': vals.get('state',False)
           })
        sale_rec_id = self.env['eon.sale.order'].create(rec_vals)
        res_vals.update({'sale_order_id': sale_rec_id.id or False})
        return res_vals
