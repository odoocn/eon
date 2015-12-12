# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class CourierTraking(models.Model):
    _name = "courier.trake"
    _description = "traking of courier and sale order"
    _rec_name = ''

    delivery_status = fields.Selection([
        ('info-received', 'Info Received'), ('in-transit', 'In Transit'),
        ('out-for-delivery', 'Out for Delivery'), ('failed-attempt', 'Failed Attempt'),
        ('delivered', 'Delivered'), ('exception', 'Exception'),
        ('expired', 'Expired'), ('pending', 'Pending')], string="Delivery Status", readonly=True)
    courier_id = fields.Many2one('couriers', string='Transporter Company', required=True, help="The partner that is doing the delivery service.")
