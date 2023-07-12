# -*- coding: utf-8 -*-
{
    'name': 'POS LoT Expiry Warning',
    'version': '13.0.1.0.1',
    'summary': 'Expiry date warning for the lot of the product',
    'category': 'Point of Sale',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'depends': [
        'point_of_sale', 'product_expiry'
    ],
    'website': 'https://cybrosys.com',
    'data': [
        'views/lot_expiry.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 4.99,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': False,
}
