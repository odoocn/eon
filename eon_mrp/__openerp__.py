{
    'name': 'Eon MRP',
    'version': '1.0',
    'category':'sale',
    'description': 'This Module Is Work as work order status.',
    'depends':['mrp','product','mrp_operations'],
    'data': [
        'wizard/wiz_eon_mrp_view.xml',
        'view/eon_mrp_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application':True,
}
