# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Odoo POS Customer Pricelist",
    "version" : "13.0.0.2",
    "category" : "Point of Sale",
    "price": 39.00,
    "currency": 'EUR',
    "depends" : ['base','sale','point_of_sale'],
    "author": "BrowseInfo",
    'summary': 'App Point of sale pricing Customer price-list on point of sales change pricelist pos price list POS product pricelist POS item pricelist on point of Sales Pricelist pos pricing Point of Sale Price Rule pos price rules pos product price pos pricelist on pos',
    "description": """
    
    Purpose :- 
This Module allows you to apply pricelist on particular customer.
    odoo POS pricelist Point of Sale Customer pricelist Pricelist on POS Customer pricelist on POS
    odoo Customer pricelist on point of sale Pricelist for customer 
    POS product pricelist POS item pricelist POS partner Pricelist POS Stock.
    odoo point of sale pricelist Point of Sale Customer pricelist Pricelist on POS Customer pricelist on POS
    odoo Customer pricelist on point of sale Pricelist for customer odoo
    POS product pricelist POS item pricelist POS partner Pricelist POS Stock.


    odoo point of sale pricelist odoo pos Customer pricelist Pricelist on point of sales Customer pricelist on point of sales
    odoo Customer pricelist on point of sales Pricelist for pos customer 
    odoo point of sales product pricelist POS item pricelist POS partner Pricelist POS Stock.

    odoo point of sale pricelist Point of Sale Customer pricelist Pricelist on POS Customer pricelist on POS
    odoo Customer pricelist on point of sale Pricelist for customer odoo
    odoo pos product pricelist POS item pricelist point of sales partner Pricelist POS Stock.
    point of sale customer pricelist point of sales customer pricelist on point of sales
    """,
    "website" : "https://www.browseinfo.in",
    "data": [
        'views/custom_pos_view.xml',
    ],
    'qweb': [
        'static/src/xml/bi_pos_customer_pricelist.xml',
    ],
    "auto_install": False,
    "installable": True,
    "live_test_url": "https://youtu.be/gzPagWsb8Do",
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
