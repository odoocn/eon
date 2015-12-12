import time
from openerp import api, fields, models
from openerp.tools import amount_to_text_en
from openerp.tools.amount_to_text_en import amount_to_text


class account_invoice(models.Model):

    _inherit = 'account.invoice'

    proforma_number = fields.Char(string="Proforma Number")
    amount_word = fields.Char(string="Amount in Words")
    proforma_id = fields.Many2one('proforma.account.invoice', string="Proforma Number")
    expire_date = fields.Date("Expire Date of Proforma")
    sale_id = fields.Many2one('sale.order', 'Sale Order')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('open', 'Open'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
       track_visibility='onchange', copy=False,
       help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
            " * The 'Pro-forma' when invoice is in Pro-forma status,invoice does not have an invoice number.\n"
            " * The 'Open' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice.\n"
            " * The 'Partial' status is set automatically when invoice is not fully paid.\n"
            " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
            " * The 'Cancelled' status is used when user cancel invoice.")

    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax
        self.amount_word = amount_to_text_en.amount_to_text(float(self.amount_total))
        return super(account_invoice, self)._compute_amount()

    @api.model
    def get_sequence(self):
        '''
            It method will be called from workflow when click on proforma button that time
            generate proforma sequence number.
        '''
        seq_no = self.env['ir.sequence'].get('account.invoice')
        self.write({'proforma_number': seq_no, 'ref_number': seq_no, 'date_invoice': time.strftime("%Y/%m/%d")})
        return True

    @api.multi
    def invoice_state(self, state):
        if self.sale_id:
            self.sale_id.sale_order_id.write({'invoice_state': state})
        return True

    @api.multi
    def action_proforma(self):
        if self.state:
            self.invoice_state(self.state)
        return True

    @api.model
    def create_proforma_invoice(self):
        account_obj = self.env['proforma.account.invoice']
        invoice_line = {}
        invoice_line_lst = []
        for account in self:
            for line in account.invoice_line:
                account_tax = ''
                for line_tax in line.invoice_line_tax_id:
                    account_tax += line_tax.name
                invoice_line = {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'account_id': line.account_id.id,
                    'unit_price': line.price_unit,
                    'invoice_line_taxes_ids': account_tax,
                    'price_sub_total': line.price_subtotal,
                    'quantity': line.quantity
                }
                invoice_line_lst.append((0, 0, invoice_line))
            vals = {
                'proforma_number': account.proforma_number,
                'partner_id': account.partner_id.id,
                'invoice_address': '',
                'delivery_address': '',
                'invoice_date': account.date_invoice,
                'invoice_line_ids': invoice_line_lst,
                'amount_untax_total': account.amount_untaxed,
                'amount_tax': account.amount_tax,
                'amount_total': account.amount_total,
                'user_id': account.user_id.id
            }
            account_id = account_obj.create(vals)
        self.write({'proforma_id': account_id.id})
        return True

    @api.multi
    def confirm_paid(self):
        res = super(account_invoice, self).confirm_paid()
        if self.state:
            self.invoice_state('paid')
        if self.sale_id.state == 'done':
            self.sale_id.sale_order_id.write({'order_state': self.sale_id.state})
        return res

    @api.multi
    def invoice_validate(self):
        res = super(account_invoice, self).invoice_validate()
        if self.state:
            self.invoice_state('open')
        return res

    @api.multi
    def action_cancel(self):
        res = super(account_invoice, self).action_cancel()
        if self.state:
            self.invoice_state('cancel')
        return res

    @api.multi
    def invoice_send_by_mail(self):
        ir_model_data = self.env['ir.model.data']

        try:
            template_id = ir_model_data.get_object_reference('eon_account', 'email_template_invoice')
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        ctx = dict()
        ctx.update({
            'default_model': 'account.invoice',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id[1],
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'attachment_use': "True",
            'attachment': "+'.pdf')",
            'target': 'new',
            'context': ctx
        }


class proforma_account_invoice(models.Model):
    _name = "proforma.account.invoice"
    _description = 'Proforma Account Invoice'
    _rec_name = 'proforma_number'

    proforma_number = fields.Char("Proforma invoice number")
    partner_id = fields.Many2one('res.partner', 'Partner')
    invoice_address = fields.Char("Invoice address")
    delivery_address = fields.Char("Delivery address")
    invoice_date = fields.Date("Invoice date")
    invoice_line_ids = fields.One2many("proforma.invoice.line", "proforma_id", string="Proforma Invoice Line")
    amount_untax_total = fields.Float("Sub Total")
    amount_tax = fields.Float("Tax")
    amount_total = fields.Float("Total Amount")
    user_id = fields.Many2one("res.users", string="Sales Person")


class proforma_invoice_line(models.Model):
    _name = "proforma.invoice.line"
    _description = 'Proforma Invoice Line'

    proforma_id = fields.Many2one("proforma.account.invoice", string="Proforma Number")
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Char("Description")
    account_id = fields.Many2one('account.account', 'Account')
    quantity = fields.Float("Quantity")
    unit_price = fields.Float("Unit Price")
    invoice_line_taxes_ids = fields.Many2many("account.tax", "rel_acc_line_tax", "rel_tax_id", "rel_pro_id", 'Taxes')
    price_sub_total = fields.Float(string="Price Sub Total")


class account_voucher(models.Model):
    _inherit = "account.voucher"

    @api.multi
    def button_proforma_voucher(self):
        res = super(account_voucher, self).button_proforma_voucher()
        active_id = self._context.get('active_id', False)
        invoice_state = ''
        if active_id:
            account_inv_rec = self.env['account.invoice'].browse(active_id)
            if account_inv_rec.residual > 0:
                account_inv_rec.write({'state': 'partial'})
                invoice_state = account_inv_rec.state
                account_inv_rec.sale_id.sale_order_id.write({'invoice_state': invoice_state})
            account_inv_rec.sale_id.sale_order_id.write({'balance': account_inv_rec.residual})
            if account_inv_rec.sale_id.invoiced and account_inv_rec.sale_id.shipped:
                account_inv_rec.sale_id.sale_order_id.write({'order_state': account_inv_rec.sale_id.state})
        return res
