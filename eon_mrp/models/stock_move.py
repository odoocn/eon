from openerp import models, _
from openerp.tools import float_compare


class stock_move(models.Model):
    _inherit = 'stock.move'

    def action_consume(self, cr, uid, ids, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False,
                       consumed_for=False, context=None):
        """ Consumed product with specific quantity from specific source location.
        @param product_qty: Consumed/produced product quantity (= in quantity of UoM of product)
        @param location_id: Source location
        @param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
        @param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
        @param consumed_for: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
        @return: New lines created if not everything was consumed for this line
        """
        if context is None:
            context = {}
        res = []
        production_obj = self.pool.get('mrp.production')
        if product_qty <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide proper quantity.'))
        #because of the action_confirm that can create extra moves in case of phantom bom, we need to make 2 loops
        ids2 = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'draft':
                ids2.extend(self.action_confirm(cr, uid, [move.id], context=context))
            else:
                ids2.append(move.id)

        prod_orders = set()
        for move in self.browse(cr, uid, ids2, context=context):
            prod_orders.add(move.raw_material_production_id.id or move.production_id.id)
            move_qty = move.product_qty
            if move_qty <= 0:
                raise osv.except_osv(_('Error!'), _('Cannot consume a move with negative or zero quantity.'))
            quantity_rest = move_qty - product_qty
            # Compare with numbers of move uom as we want to avoid a split with 0 qty
            self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, product_qty, move.product_uom)
            quantity_rest_uom = move.product_uom_qty - self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, product_qty, move.product_uom)
            if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) != 0:
                print "Split Create:::MV:::",
                new_mov = self.split(cr, uid, move, product_qty, context=context)
                if move.production_id:
                    self.write(cr, uid, [new_mov], {'production_id': move.production_id.id}, context=context)
                res.append(new_mov)
            vals = {'restrict_lot_id': restrict_lot_id,
                    'restrict_partner_id': restrict_partner_id,
                    'consumed_for': consumed_for}
            if location_id:
                vals.update({'location_id': location_id})
            self.write(cr, uid, [move.id], vals, context=context)
        # Original moves will be the quantities consumed, so they need to be done
        self.action_done(cr, uid, ids2, context=context)
        if res:
            self.action_assign(cr, uid, res, context=context)
        if prod_orders:
            production_obj.signal_workflow(cr, uid, list(prod_orders), 'button_produce')
        return res

    def split(self, cr, uid, move, qty, restrict_lot_id=False, restrict_partner_id=False, context=None):
            """ Splits qty from move move into a new move
            :param move: browse record
            :param qty: float. quantity to split (given in product UoM)
            :param restrict_lot_id: optional production lot that can be given in order to force the new move to restrict its choice of quants to this lot.
            :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
            :param context: dictionay. can contains the special key 'source_location_id' in order to force the source location when copying the move

            returns the ID of the backorder move created
            """
            if move.state in ('done', 'cancel'):
                raise osv.except_osv(_('Error'), _('You cannot split a move done'))
            if move.state == 'draft':
                #we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
                #case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
                raise osv.except_osv(_('Error'), _('You cannot split a draft move. It needs to be confirmed first.'))

            if move.product_qty <= qty or qty == 0:
                return move.id

            uom_obj = self.pool.get('product.uom')
            context = context or {}
            #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
            uom_qty = uom_obj._compute_qty_obj(cr, uid, move.product_id.uom_id, qty, move.product_uom, rounding_method='HALF-UP', context=context)
            uos_qty = uom_qty * move.product_uos_qty / move.product_uom_qty
            ctx = context.copy()
            ctx['do_not_propagate'] = True
            self.write(cr, uid, [move.id], {
                'product_uom_qty': qty,
                'product_uos_qty': move.product_uos_qty - uos_qty,
            }, context=ctx)
            #returning the first element of list returned by action_confirm is ok because we checked it wouldn't be exploded (and
            #thus the result of action_confirm should always be a list of 1 element length)
            return self.action_confirm(cr, uid, [move.id], context=context)[0]
