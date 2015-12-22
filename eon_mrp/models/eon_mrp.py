from openerp import fields, models, api, tools
from openerp.tools import frozendict
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.addons.product import _common
from datetime import datetime
import time

class mrp_production(models.Model):
    _inherit = 'mrp.production'

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce in the uom of the production order
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get("product.uom")
        production = self.browse(cr, uid, production_id, context=context)
        production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')
        main_production_move = False
        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            produced_products = {}

            for produce_product in production.move_created_ids:
                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                lot_id = False
                if wiz:
                    lot_id = wiz.lot_id.id
                qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity
                new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], qty,
                                                         location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)
                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
#            for consume in consume_lines:
#                remaining_qty = consume['product_qty']
#                for raw_material_line in production.move_lines:
#                    if raw_material_line.state in ('done', 'cancel'):
#                        continue
#                    if remaining_qty <= 0:
#                        break
#                    if consume['product_id'] != raw_material_line.product_id.id:
#                        continue
#                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
#                    rt = stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id,
#                                                 restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
#                    remaining_qty -= consumed_qty
#                if not float_is_zero(remaining_qty, precision_digits=precision):
#                    #consumed more in wizard than previously planned
#                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
#                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, False, 0, context=context)
#                    stock_mov_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': consume['lot_id'],
#                                                                    'consumed_for': main_production_move}, context=context)
#                    res_done = stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)
        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)
        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_lines:
            stock_mov_obj.action_cancel(cr, uid, [x.id for x in production.move_lines], context=context)
        self.signal_workflow(cr, uid, [production_id], 'button_produce_done')
        return True
    
    

class mrp_production_workcenter_line(models.Model):
    _inherit = "mrp.production.workcenter.line"

    input_qty = fields.Float(string="Input Quantity", requred=True)
    output_qty = fields.Float(string="Output Quantity", requred=True)
    diff_qty = fields.Float(string="Difference Quantity", readonly=True)
    missing_reason = fields.Many2one("mrp.production.missing")
    wiz_count = fields.Integer('Count', readonly=True)
    workorder_code = fields.Selection([
                                    ('rmc','Raw materials counting'),
                                    ('rmqc','Raw materials quality cheking'),
                                    ('unpacked','Unpacked'),
                                    ('semipacked','Semipacked'),
                                    ('packed','Packed')], 'Routing Code', readonly=True, requred=True)

    @api.multi
    def start_wiz_call(self):
        form_view_id = self.env['ir.model.data'].get_object_reference('eon_mrp', 'wiz_input_form_view')[1]
        if self.wiz_count <= 0:
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
    def modify_production_order_state(self, cr, uid, ids, action):
        """ Modifies production order state if work order state is changed.
        @param action: Action to perform.
        @return: Nothing
        """
        prod_obj_pool = self.pool.get('mrp.production')
        oper_obj = self.browse(cr, uid, ids)[0]
        prod_obj = oper_obj.production_id
        if action == 'start':
            if prod_obj.state == 'confirmed':
                prod_obj_pool.force_production(cr, uid, [prod_obj.id])
                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_ produce')
            elif prod_obj.state == 'ready':
                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_produce')
            elif prod_obj.state == 'in_production':
                return
            else:
                raise osv.except_osv(_('Error!'), _('Manufacturing order cannot be started in state "%s"!') % (prod_obj.state,))
        else:
            open_count = self.search_count(cr, uid, [('production_id', '=', prod_obj.id), ('state', '!=', 'done')])
            flag = not bool(open_count)
            if flag:
                for production in prod_obj_pool.browse(cr, uid, [prod_obj.id], context= None):
                    res = prod_obj_pool.action_produce(cr, uid, production.id, oper_obj.output_qty, 'consume_produce', context = None)
                prod_obj_pool.signal_workflow(cr, uid, [oper_obj.production_id.id], 'button_produce_done')
        return

    @api.multi
    def action_done(self):
        """ Sets state to done, writes finish date and calculates delay.
        @return: True
        """
        res = super(mrp_production_workcenter_line, self).action_done()
#        self.modify_production_order_state('done')
        # wiz_mrp_obj = self.env['wiz.mrp.order']
        for work_order_rec in self:
            work_order_ids = False
            if work_order_rec.production_id:
                work_order_ids = self.search([('production_id', '=', work_order_rec.production_id.id), ('state', '=', 'draft')])
                if work_order_rec.state == 'done':
                    work_order_ids.write({'input_qty': work_order_rec.output_qty})
        return res


class missing_reason(models.Model):
    _name = "mrp.production.missing"

    missing_reason = fields.Char(string="Missing product reason")


class mrp_routing_workcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    routing_code = fields.Selection([('rmc','Raw materials counting'),
                                    ('rmqc','Raw materials quality cheking'),
                                    ('unpacked','Unpacked'),
                                    ('semipacked','Semipacked'),
                                    ('packed','Packed')], 'Routing Code')


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
                raise osv.except_osv(_('Invalid Action!'), _('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.name, bom_line_id.product_id.name_get()[0][1]))

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
                raise osv.except_osv(_('Invalid Action!'), _('BoM "%s" contains a phantom BoM line but the product "%s" does not have any BoM defined.') % (master_bom.name, bom_line_id.product_id.name_get()[0][1]))
        return result, result2
