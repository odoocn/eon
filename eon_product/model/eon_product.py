from openerp import api, fields, models


class product_template(models.Model):

    _inherit = 'product.template'
    _rec_name = 'name'

    # wastage = fields.Float(string="Wastage")
    # packing_product = fields.Float(string="Packing Product")
    # raw_materials_prod = fields.Float(string="Raw Materials Of Product")
    rmc = fields.Integer('Raw materials counting')
    rmqc = fields.Integer('Raw materials quality cheking')
    unpacked = fields.Integer('Unpacked', help="Cleaning Drying and Sealing")
    semipacked = fields.Integer('Semipacked', help="Sterilization")
    packed = fields.Integer('Packed', help="Stricking and Box packing")
