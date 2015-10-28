from openerp import fields, models, api, tools
from openerp.tools import frozendict
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.addons.product import _common
from datetime import datetime
import time

class mrp_production_workcenter_line(models.Model):
    _inherit = "mrp.production.workcenter.line"

    input_qty = fields.Float(string="Input Quantity", requred=True)
    output_qty = fields.Float(string="Output Quantity", requred=True)
    diff_qty = fields.Float(string="Difference Quantity", readonly=True)
    missing_reason = fields.Many2one("mrp.production.missing")
    wiz_count = fields.Integer('Count', readonly=True) 
    workorder_code = fields.Char('Routing Code')

    @api.multi
    def start_wiz_call(self):
        form_view_id = self.env['ir.model.data'].get_object_reference('eon_mrp', 'wiz_input_form_view')[1]
        print "\n\n\nself.wiz_count::::::::::",self.wiz_count
        if self.wiz_count <= 0:
            print "\n\n\nWizard.....Callled......"
            return {
                'type': 'ir.actions.act_window',
                'name': 'Input Quantity',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wiz.input.mrp.order',
                'views': [(form_view_id, 'form')],
                'target': 'new',
            }
        else:
            self.signal_workflow('button_start_working')
            return True

#    @api.cr_uid_ids
#    def modify_production_order_state(self, cr, uid, ids, action):
#        """ Modifies production order state if work order state is changed.
#        @param action: Action to perform.
#        @return: Nothing
#        """
#        print "\n\n\nAction:::base....;;",action, self
#        res = super(mrp_production_workcenter_line, self).modify_production_order_state(cr, uid, ids, action)
#        print "\n\n\n\nSuper Callllled....",res
# # #        prod_obj_pool = self.pool.get('mrp.production')
# #        oper_obj = self.browse(cr, uid, ids)[0]
# # #        prod_obj = oper_obj.production_id
# # #        if action == 'start':
# # #            if prod_obj.state =='confirmed':
# # #                prod_obj_pool.force_production(cr, uid, [prod_obj.id])
# # #                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_ produce')
# # #            elif prod_obj.state =='ready':
# # #                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_produce')
# # #            elif prod_obj.state =='in_production':
# # #                return
# # #            else:
# # #                raise osv.except_osv(_('Error!'),_('Manufacturing order cannot be started in state "%s"!') % (prod_obj.state,))
# # #        else:
# # #            open_count = self.search_count(cr,uid,[('production_id','=',prod_obj.id), ('state', '!=', 'done')])
# # #            print "\n\n\\n\n\n\nCount........",open_count
# # #            flag = not bool(open_count)
# # #            print "\n\n\nFlaggggg:::",flag
# # #            if flag:
# # #                print "\n\n\n\nprod_obj.id::::uppbase:::jjjj:::::",prod_obj.id
# # #                for production in prod_obj_pool.browse(cr, uid, [prod_obj.id], context= None):
# # #                    print "\n\n\nBase...production.move_lines or production.move_created_ids::Base...MV Line::hhhhhhhh::ggg::",production.move_lines, production.move_created_ids
# # #                    print "\n\n\n\n...oper_obj:::base::finbalqtyyy::.",oper_obj.output_qty
# # #                    if production.move_lines or production.move_created_ids:
# # #                        res = prod_obj_pool.action_produce(cr,uid, production.id, oper_obj.output_qty, 'consume_produce', context = None)
# # #                        print "\n\n\n\nres::::::::caaallled....get::::::called::;;",res
# # #                prod_obj_pool.signal_workflow(cr, uid, [oper_obj.production_id.id], 'button_produce_done')
#        move_id = self.pool.get('stock.move').search(cr, uid, [('name','=',oper_obj.name)])
#        print "\n\n\n\n\nGet Move_ID::::::::::::",move_id,oper_obj.name,oper_obj
#        dffff
#        return


#    @api.multi
#    def action_done(self):
#        """ Sets state to done, writes finish date and calculates delay.
#        @return: True
#        """
#        print "\n\nAction done () Called..overriteeeee2..jkkkkk..",self
#        res = super(mrp_production_workcenter_line, self).action_done()
#        delay = 0.0
#        date_now = time.strftime('%Y-%m-%d %H:%M:%S')
#        print "\n\n\n\nself.ids[0]::::::::::::",self.ids[0]
#        ids = self.ids
#        print "\n\n\n\nWork Order Ids::::",ids
#        obj_line = self.browse(ids)
#        print "\n\n\n\nobj_line::::::::::",obj_line
#        date_start = datetime.strptime(obj_line.date_start,'%Y-%m-%d %H:%M:%S')
#        date_finished = datetime.strptime(date_now,'%Y-%m-%d %H:%M:%S')
#        delay += (date_finished-date_start).days * 24
#        delay += (date_finished-date_start).seconds / float(60*60)
#
#        self.write({'state':'done', 'date_finished': date_now,'delay': delay})
#        cr, uid, context = self.env.args
#
#        resd = self.modify_production_order_state('done')
#        print "\n\n\nresd:::::::::::::",resd
#        
#        print "\n\n Res.......",res
#        wiz_mrp_obj = self.env['wiz.mrp.order']
#        for work_order_rec in self:
#            work_order_ids = False
#            if work_order_rec.production_id:
#                work_order_ids = self.search([('production_id','=',work_order_rec.production_id.id),('state','=','draft')])
#                if work_order_rec.state == 'done':
#                    work_order_ids.write({'input_qty': work_order_rec.output_qty})
#        return res


    def action_done(self, cr, uid, ids, context=None):
        """ Sets state to done, writes finish date and calculates delay.
        @return: True
        """
        print "\n\nAction done () Called..overriteeeee2....",self
        res = super(mrp_production_workcenter_line, self).action_done(cr, uid, ids, context=context)
        delay = 0.0
        date_now = time.strftime('%Y-%m-%d %H:%M:%S')
        obj_line = self.browse(cr, uid, ids[0], context=context)
        print "\n\n\n\nobj_line:::::::::::::",obj_line

        date_start = datetime.strptime(obj_line.date_start,'%Y-%m-%d %H:%M:%S')
        date_finished = datetime.strptime(date_now,'%Y-%m-%d %H:%M:%S')
        delay += (date_finished-date_start).days * 24
        delay += (date_finished-date_start).seconds / float(60*60)

        self.write(cr, uid, ids, {'state':'done', 'date_finished': date_now,'delay':delay}, context=context)
        self.modify_production_order_state(cr,uid,ids,'done')
        print "\n\n Res.......",res
        wiz_mrp_obj = self.pool.get('wiz.mrp.order')
        work_order_line = self.pool.get('mrp.production.workcenter.line')
        for work_order_rec in obj_line:
            work_order_ids = False
            if work_order_rec.production_id:
                work_order_ids = self.search(cr, uid, [('production_id','=',work_order_rec.production_id.id),('state','=','draft')], context=context)
                print "\n\n\nwork_order_ids:::::::::::::::",work_order_ids
                if work_order_rec.state == 'done':
#                    updt = work_order_ids.write({'input_qty': work_order_rec.output_qty})
                    updt = work_order_line.write(cr, uid, work_order_ids, {'input_qty': work_order_rec.output_qty}, context=context)
                    print "\n\n\n\n\n\nupdt::::::::::",updt
        return res



class missing_reason(models.Model):
    _name = "mrp.production.missing"

    missing_reason = fields.Char(string="Missing product reason")

class mrp_routing_workcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    routing_code = fields.Char('Routing Code')

class mrp_bom(models.Model):
    _inherit = 'mrp.bom'
    
    @api.cr_uid_context
    def _bom_explode(self, cr, uid, bom, product, factor, properties=None, level=0, routing_id=False, previous_products=None, master_bom=None, context=None):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product template.
        @param product: Select a particular variant of the BoM. If False use BoM without variants.
        @param factor: Factor represents the quantity, but in UoM of the BoM, taking into account the numbers produced by the BoM
        @param properties: A List of properties Ids.
        @param level: Depth level to find BoM lines starts from 10.
        @param previous_products: List of product previously use by bom explore to avoid recursion
        @param master_bom: When recursion, used to display the name of the master bom
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        res = super(mrp_bom, self)._bom_explode(cr, uid, bom, product, factor, properties=properties, level=level, routing_id=routing_id, previous_products=previous_products, master_bom=master_bom, context=context)
        uom_obj = self.pool.get("product.uom")
        routing_obj = self.pool.get('mrp.routing')
        master_bom = master_bom or bom
    
        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            factor = _common.ceiling(factor, product_rounding)
            if factor < product_rounding:
                factor = product_rounding
            return factor
    
        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)
    
        result = []
        result2 = []
    
        routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
        if routing:
            for wc_use in routing.workcenter_lines:
                wc = wc_use.workcenter_id
                d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                mult = (d + (m and 1.0 or 0.0))
                cycle = mult * wc_use.cycle_nbr
                result2.append({
                    'name': tools.ustr(wc_use.name) + ' - ' + tools.ustr(bom.product_tmpl_id.name_get()[0][1]),
                    'workcenter_id': wc.id,
                    'sequence': level + (wc_use.sequence or 0),
                    'cycle': cycle,
                    'hour': float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
                    'workorder_code': wc_use.routing_code,
                })
    
        for bom_line_id in bom.bom_line_ids:
            if self._skip_bom_line(cr, uid, bom_line_id, product, context=context):
                continue
            if set(map(int, bom_line_id.property_ids or [])) - set(properties or []):
                continue
    
            if previous_products and bom_line_id.product_id.product_tmpl_id.id in previous_products:
                raise osv.except_osv(_('Invalid Action!'), _('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.name,bom_line_id.product_id.name_get()[0][1]))
    
            quantity = _factor(bom_line_id.product_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding)
            bom_id = self._bom_find(cr, uid, product_id=bom_line_id.product_id.id, properties=properties, context=context)
    
            #If BoM should not behave like PhantoM, just add the product, otherwise explode further
            if bom_line_id.type != "phantom" and (not bom_id or self.browse(cr, uid, bom_id, context=context).type != "phantom"):
                result.append({
                    'name': bom_line_id.product_id.name,
                    'product_id': bom_line_id.product_id.id,
                    'product_qty': quantity,
                    'product_uom': bom_line_id.product_uom.id,
                    'product_uos_qty': bom_line_id.product_uos and _factor(bom_line_id.product_uos_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding) or False,
                    'product_uos': bom_line_id.product_uos and bom_line_id.product_uos.id or False,
                })
            elif bom_id:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(cr, uid, bom_id, context=context)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(cr, uid, bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.product_qty
                res = self._bom_explode(cr, uid, bom2, bom_line_id.product_id, quantity2,
                    properties=properties, level=level + 10, previous_products=all_prod, master_bom=master_bom, context=context)
                result = result + res[0]
                result2 = result2 + res[1]
            else:
                raise osv.except_osv(_('Invalid Action!'), _('BoM "%s" contains a phantom BoM line but the product "%s" does not have any BoM defined.') % (master_bom.name,bom_line_id.product_id.name_get()[0][1]))
        return result, result2
