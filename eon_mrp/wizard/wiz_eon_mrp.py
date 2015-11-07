from openerp import api, fields, models
from openerp.exceptions import ValidationError


class wiz_mrp_order(models.TransientModel):
    _name = 'wiz.mrp.order'
    qty_output = fields.Float('Output Qty')
    mrp_order_id = fields.Many2one('mrp.production.workcenter.line', 'Order Line')

    @api.multi
    def get_output_qty(self):
        active_id = self._context['active_id']
        if active_id:
            mrp_line_obj = self.env['mrp.production.workcenter.line']
            mrp_line_rec = mrp_line_obj.browse(active_id)
            if mrp_line_rec.production_id:
                work_order_ids = self.env['wiz.input.mrp.order'].get_mrp_line_rec(mrp_line_rec.production_id.id)
                for work_order_line in work_order_ids:
                    tot_qty = work_order_line.qty
                    if work_order_line.state == 'draft':
                        res = work_order_line.write({'input_qty': self.qty_output})
                work_count = mrp_line_obj.search_count([('production_id', '=', mrp_line_rec.production_id.id), ('state', 'not in', ['done', 'cancel'])])
                vals = {}
                if self.qty_output != 0.0 and self.qty_output <= mrp_line_rec.input_qty:
                    vals.update({'output_qty': self.qty_output})
                else:
                    raise ValidationError('Please Enter Quantity in Output Qty! \n or \n You should be enter quantity from quantity in output qty.')
#                if work_count == 1:
#                    vals.update({'qty': self.qty_output})
                mrp_line_rec.write(vals)
                raw_count = 0
                raw_qual_check = 0
                unpacked = 0
                semipacked = 0
                packed = 0
                output_qty = self.qty_output
                if mrp_line_rec.workorder_code == 'RMC':
                    rmc_qty = mrp_line_rec and mrp_line_rec.production_id and mrp_line_rec.production_id.product_id and mrp_line_rec.production_id.product_id.rmc
                    raw_qual_check = output_qty
                    raw_count = mrp_line_rec.input_qty - rmc_qty
                elif mrp_line_rec.workorder_code == 'RMQC':
                    unpacked = output_qty
                elif mrp_line_rec.workorder_code in ['CL', 'DRY']:
                    unpacked = output_qty
                elif mrp_line_rec.workorder_code == 'SEL':
#                    unpacked = output_qty
                    semipacked = output_qty
                elif mrp_line_rec.workorder_code == 'STER':
                    packed = output_qty
                elif mrp_line_rec.workorder_code in ['STICK', 'BXP']:
                    packed = output_qty
                mrp_line_rec.production_id.product_id.write({'semipacked': semipacked, 'packed': packed, 'unpacked': unpacked, 'rmqc': raw_qual_check, 'rmc': raw_count})
            mrp_line_rec.signal_workflow('button_done')
        return True

    @api.multi
    def get_close_wiz(self):
        active_id = self._context['active_id']
        if active_id:
            mrp_line_rec = self.env['mrp.production.workcenter.line'].browse(active_id)
            mrp_line_rec.write({'state': 'startworking'})
        return {
            'type': 'ir.actions.act_window_close',
        }


class wiz_input_qty_mrp_order(models.TransientModel):
    _name = 'wiz.input.mrp.order'

    @api.model
    def _get_input_qty(self):
        active_id = self._context.get('active_id', False)
        if active_id:
            order_line = self.env['mrp.production.workcenter.line'].browse(active_id)
            return order_line.qty
#            for order_line in self.env['mrp.production.workcenter.line'].browse(active_id):
#                print "\n\norder_line::qtyyy::",order_line.qty
#                self.input_qty = order_line.qty
#            print "\n\nself.input_qty::::",self.input_qty

    input_qty = fields.Float('Input Qty', default=_get_input_qty)

    @api.multi
    def get_input_wizard_view(self):
        form_view_id = self.env['ir.model.data'].get_object_reference('eon_mrp', 'wiz_input_form_view')[1]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Start Wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wiz.input.mrp.order',
            'views': [(form_view_id, 'form')],
            'target': 'new',
        }

    @api.multi
    def get_input_qty(self):
        active_id = self._context['active_id']
        mrp_line_obj = self.env['mrp.production.workcenter.line']
        if active_id:
            mrp_line_rec = mrp_line_obj.browse(active_id)
            if self.input_qty != 0.0 and self.input_qty <= mrp_line_rec.qty:
                res = mrp_line_rec.write({'input_qty': self.input_qty})
            else:
                raise ValidationError('You are do not enter negative value in Input Qty \n OR \n You should be enter available Quantity from quantity in Input Qty! ')
            if mrp_line_rec.workorder_code == 'RMC':
                mrp_line_rec.production_id.product_id.write({'rmc': self.input_qty})
        
        if mrp_line_rec.production_id:
            work_order_ids = self.get_mrp_line_rec(mrp_line_rec.production_id.id)
            for work_order_line in work_order_ids:
                if work_order_line.state == 'draft':
                    work_order_line.write({'wiz_count': 1})
            mrp_line_rec.signal_workflow('button_start_working')
            print "\n\nres::::::::::::",res
            print "\n\nmrp_line_rec:::::",mrp_line_rec
        return True

    @api.multi
    def get_close_wiz(self):
        active_id = self._context['active_id']
        if active_id:
            mrp_line_rec = self.env['mrp.production.workcenter.line'].browse(active_id)
            res = mrp_line_rec.write({'state': 'draft'})
        return {
            'type': 'ir.actions.act_window_close',
        }

    @api.multi
    def get_mrp_line_rec(self, production_id):
        mrp_line_obj = self.env['mrp.production.workcenter.line']
        work_order_ids = mrp_line_obj.search([('production_id','=',production_id),('state','=','draft')])
        return work_order_ids
