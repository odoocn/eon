{
    'name': 'Eon Account',
    'version': '1.0',
    'category':'sale',
    'description': 'This Module Is Work as Consumer Invoice Generate.',
    'depends':['sale','mrp','product','stock','account'],
    'data': [
             'eon_account_view.xml',
             'workflow/account_invoice_workflow.xml',
             'sequence/invoice_sequence.xml',
             'report_invoice_template.xml',
             'eon_invoice_report.xml',
             'data/invoice_template_data.xml'
        ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application':True,
}