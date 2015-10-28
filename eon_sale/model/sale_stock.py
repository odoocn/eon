from openerp import _, models, fields, api

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.multi
    def do_detailed_transfer(self):
        res = super(stock_transfer_details, self).do_detailed_transfer()
        if self.picking_id.id:
            rec = self.picking_id.sale_id.sale_order_id.write({'picking_state': self.picking_id.state})
            sale_order_id = self.picking_id.sale_id.sale_order_id
            picking_state = self.picking_id.state
            self.picking_id.move_line_update(sale_order_id, picking_state)
            sale_rec = self.picking_id.sale_id or False
            if sale_rec.invoiced and sale_rec.shipped:
               res = sale_rec.sale_order_id.write({'order_state': sale_rec.state})
        return res

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def move_line_update(self, sale_order_id, state):
        move_line_lst = []
        for move_line in sale_order_id.move_ids:
            backorder_id = self.sale_id.sale_order_id.backorder_id or False
            if move_line.state and move_line.state not in ['confirmed','done'] and backorder_id:
                move_line_lst.append((1, move_line.id,{'state': state}))
            if backorder_id:
                if backorder_id.state == 'done' and move_line.state != 'done':
                    move_line_lst.append((1, move_line.id,{'state': state}))
            if not backorder_id:
                move_line_lst.append((1, move_line.id,{'state': state}))
        rec = self.sale_id.sale_order_id.write({'picking_state': state,'move_ids': move_line_lst})
        return True

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        print "Action Asssign::::",self.state
        res = super(stock_picking, self).action_assign()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            self.move_line_update(sale_order_id, self.state)
        return True

    @api.multi
    def force_assign(self):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        print "\nForce Assign:::::::",self.state
        res = super(stock_picking, self).force_assign()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            self.move_line_update(sale_order_id, self.state)
        return True

    @api.multi
    def action_cancel(self):
        print "\n\nAction Cancellllll",self.state
        res = super(stock_picking, self).action_cancel()
        if self.sale_id:
            sale_order_id = self.sale_id.sale_order_id
            rec = self.sale_id.sale_order_id.write({'order_state': 'shipping_except'})
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
        return True
#
#    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
#        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
#        """
#        backorder_id = super(stock_picking, self)._create_backorder(cr, uid, picking, backorder_moves=[], context=context)
#        vals = {}
#        mv_line_lst = []
#        if backorder_id:
#            for move_line in self.browse(cr, uid, backorder_id, context=context).move_lines:
#                vals.update({
#                        'product_id' : move_line.product_id.id,
#                        'qty': move_line.product_uom_qty,
#                        'uom_id': move_line.product_uom.id,
#                        'state': move_line.state,
#                        'source_location_id': move_line.location_id.id,
#                        'destination_location_id': move_line.location_dest_id.id,
#                        'sale_order_id': picking.sale_id.sale_order_id.id
#                    })
#                res = picking.sale_id.sale_order_id.write({'backorder_id': backorder_id})
#                picking = self.pool['eon.stock.move.line'].create(cr, uid, vals, context=context)
#            return backorder_id
#        return False

class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
        (and company). Those attributes are also given as parameters.
        """
        res = super(stock_move, self)._picking_assign(cr, uid, move_ids, procurement_group, location_from, location_to, context=context)
        print "\n\nPicking Asssig Calllled........",move_ids
#        print "\n\n\Stateeee::::",self.picking_id
        sale_id = False
        state = ''
        picking_rec = False
        for mv_line in self.browse(cr, uid, move_ids, context=context):
            move_line_lst = []
            state = mv_line.picking_id.state
            for move_line in mv_line.picking_id.sale_id.sale_order_id.move_ids:
                move_line_lst.append((1, move_line.id,{'state': state}))
            picking_rec = mv_line.picking_id
        rec = picking_rec.sale_id.sale_order_id.write({'picking_state': state,'move_ids': move_line_lst})
        print "\n\nUpdated.......MV :::::",rec
        return True
