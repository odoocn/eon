# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Delivery Couriers',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Allows you to add delivery methods in sale orders and picking.
==============================================================

You can define your own carrier for prices. When creating
invoices from picking, the system is able to add and compute the shipping line.
""",
    'depends': ['delivery'],
    'data': [
        'data/aftership.xml',
        'views/courier.xml',
    ],
    'demo': [],
    'test': [],
}
