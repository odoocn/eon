# -*- coding: utf-8 -*-
from openerp.addons.couriers.models import aftership
from openerp import api, fields, models


class Couriers(models.Model):
    _name = "courier.courier"
    _description = "all courier name from aftership"
    _rec_name = "name"

    name = fields.Char(string='Courier name', required=True)
    phone = fields.Char(string='Phone number')
    web_url = fields.Char(string='Website url')
    other_name = fields.Char(string='alter name')
    slug = fields.Char(string='Code of courier')
    default_language = fields.Char(string='Default language')
    rec_field_ids = fields.One2many('couriers.required.field', 'c_id')
    is_required_fiedls = fields.Boolean('Is any required fields', default=False)

    @api.multi
    def action_get_courier_list(self):
        print "=-===self=======", self
        api = aftership.APIv4('27f1f4cc-0955-43d9-9cfe-478c14f61847')
        # api_key = self.env["ir.config_parameter"].get_param("courier_api_key", default='')
        api_key = self.env['delivery.carrier'].search([('delivery_type', '=', 'aftership')], limit=1)
        print " api key", api_key.courier_api_key
        # api = aftership.APIv4('27f1f4cc-0955-43d9-9cfe-478c14f61847')
        # print "=======code", api.get('code')
        couriers = api.couriers.all.get()
        print "-------------", couriers, "\n\n\n\n"

        print "==============", couriers.get('code', False)
        print "================", couriers.get('couriers', False)
        stored_couriers = map(lambda item: item['name'], self.search_read([], ['name']))
        for courier in couriers.get('couriers', False):
            if courier['name'] not in stored_couriers:
                vals = {
                    'name': courier.get('name'),
                    'phone': courier.get('phone'),
                    'web_url': courier.get('web_url'),
                    'other_name': courier.get('other_name'),
                    'slug': courier.get('slug'),
                    'default_language': courier.get('default_language'),
                    'is_required_fiedls': True if courier.get('required_fields') else False,
                }
                c_id = self.create(vals)
                for c in courier.get('required_fields'):
                    self.env['couriers.required.field'].create({'c_id': c_id.id, 'requied_name': c})


class CourierRequired(models.Model):
    _name = 'couriers.required.field'

    c_id = fields.Many2one('courier.courier', string='courier')
    requied_name = fields.Char(string="Required Field")

    @api.model
    def create(self, vals):
        super(CourierRequired, self).create(vals)


# class MyStockConfiguration(models.TransientModel):
#     _inherit = 'stock.config.settings'

#     courier_api_key = fields.Char(string="courier api key")

#     @api.model
#     def set_courier_api_key(self, ids):
#         self.env['ir.config_parameter'].set_param('courier_api_key', self.browse(ids[0]).courier_api_key or '')

#     @api.model
#     def get_default_courier_api_key(self, ids):
#         courier_api_key = self.env['ir.config_parameter'].get_param('courier_api_key', default='')
#         return dict(courier_api_key=courier_api_key)

#     @api.multi
#     def action_get_courier_list(self):
#         self.env['courier.courier'].action_get_courier_list()
#         return


class CourierPartner(models.Model):
    _inherit = 'stock.picking'

    transporter = fields.Many2one('courier.courier', string='Transporter Company', help="The partner that is doing the delivery service.")

    def genarate_traking_link(self):
        return "https://track.aftership.com/%s/%s" % (self.transporter.slug, self.carrier_tracking_ref)

    @api.multi
    def open_website_url(self):
        self.ensure_one()
        print "==============", self.genarate_traking_link()
        client_action = {'type': 'ir.actions.act_url',
                         'name': "Shipment Tracking Page",
                         'target': 'new',
                         'url': self.genarate_traking_link()
                         }
        return client_action


class DeliveryTraking(models.Model):
    _inherit = 'delivery.grid'

    delivery_type = fields.Selection(selection_add=[('aftership', "Aftership")])
    courier_api_key = fields.Char(string="courier api key")

    @api.multi
    def action_get_courier_list(self):
        self.env['courier.courier'].action_get_courier_list()
        return

    def aftership_get_tracking_link(self, pickings):
        res = []
        for picking in pickings:
            print "=="
        return res


# class SaleOrder(models.Model):
    # _inherit = 'sale.order'

    # delivery_type = fields.Selection(selection_add=[('aftership', "Aftership")])
