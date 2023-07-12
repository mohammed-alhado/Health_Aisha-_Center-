# -*- coding: utf-8 -*-
{
    'name': "Material Request",

    'summary': """
        Request material from Purchase and inventory""",

    'description': """
        Request material from Purchase and inventory
    """,

    'author': "abonwader",

   
    'category': 'Uncategorized',
    'version': '13.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','oehealth_all_in_one'],

    # always loaded
    'data': [
        'security/material_group.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    
}
