# -*- coding: utf-8 -*-

from openerp import api, fields, models, _


class sale_advance_payment_inv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"
