# -*- coding: utf-8 -*-

from openerp import api, models


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.multi
    def do_detailed_transfer(self):
        res = super(stock_transfer_details, self).do_detailed_transfer()
        if self.picking_id.id:
            self.picking_id.sale_id.sale_order_id.write({'picking_state': self.picking_id.state})
            sale_order_id = self.picking_id.sale_id.sale_order_id
            picking_state = self.picking_id.state
            mv_line_lst = []
            for transfer_line in self.item_ids:
                for move_line in self.picking_id.sale_id.sale_order_id.move_ids:
                    for line in self.picking_id.sale_id.sale_order_id.backorder_id.move_lines:
                        if transfer_line.quantity != move_line.qty:
                            mv_line_lst.append((1, move_line.id, {'qty': transfer_line.quantity}))
                if mv_line_lst:
                    self.picking_id.move_line_update(sale_order_id, picking_state)
        return res


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def move_line_update(self, sale_order_id, state):
        move_line_lst = []
        for move_line in sale_order_id.move_ids:
            if move_line.state and move_line.state:
                move_line_lst.append((1, move_line.id, {'state': state}))
        self.sale_id.sale_order_id.write({'picking_state': 'partially_availible', 'move_ids': move_line_lst})
        return True

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        super(stock_picking, self).action_assign()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            self.move_line_update(sale_order_id, self.state)
        return True

    @api.multi
    def force_assign(self):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        res = super(stock_picking, self).force_assign()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            self.move_line_update(sale_order_id, self.state)
        return res

    @api.multi
    def action_cancel(self):
        res = super(stock_picking, self).action_cancel()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            self.sale_id.sale_order_id.write({'order_state': 'shipping_except'})
            self.move_line_update(sale_order_id, self.state)
        return res

    @api.multi
    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        res = super(stock_picking, self).action_done()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            self.move_line_update(sale_order_id, self.state)
        return res

    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        backorder_id = super(stock_picking, self)._create_backorder(cr, uid, picking, backorder_moves=[], context=context)
        vals = {}
        if backorder_id:
            for move_line in self.browse(cr, uid, backorder_id, context=context).move_lines:
                vals.update({
                            'product_id': move_line.product_id.id,
                            'qty': move_line.product_uom_qty,
                            'uom_id': move_line.product_uom.id,
                            'state': 'confirmed',
                            'source_location_id': move_line.location_id.id,
                            'destination_location_id': move_line.location_dest_id.id,
                            'sale_order_id': picking.sale_id.sale_order_id.id})
                self.write(cr, uid, backorder_id, {'state': 'confirmed'}, context=context)
                picking.sale_id.sale_order_id.write({'backorder_id': backorder_id})
                picking = self.pool['eon.stock.move.line'].create(cr, uid, vals, context=context)
            return backorder_id
        return False


class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
        (and company). Those attributes are also given as parameters.
        """
        res = super(stock_move, self)._picking_assign(cr, uid, move_ids, procurement_group, location_from, location_to, context=context)
        state = ''
        picking_rec = False
        for mv_line in self.browse(cr, uid, move_ids, context=context):
            move_line_lst = []
            state = mv_line.picking_id.state
            for move_line in mv_line.picking_id.sale_id.sale_order_id.move_ids:
                move_line_lst.append((1, move_line.id, {'state': state}))
            picking_rec = mv_line.picking_id
        picking_rec.sale_id.sale_order_id.write({'picking_state': state, 'move_ids': move_line_lst})
        return res
