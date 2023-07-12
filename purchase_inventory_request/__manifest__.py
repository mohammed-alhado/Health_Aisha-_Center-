
{
    'name': 'Purchase & inventory request',
    'version': '13.1.0.0',
    'category': 'Purchase',
    'author': 'ahmed yahia',
    'summary': 'request Purchase order or inventory transfer from Hospital department',
    'description': """
    """,
    'depends': ['base_setup','purchase'],
    'data': [
        'security/request_security.xml',
        'security/ir.model.access.csv',
        'views/purchase_view.xml',
        # 'views/inventory_view.xml',
    ],
    'installable': True,  
    'application': False,
}
