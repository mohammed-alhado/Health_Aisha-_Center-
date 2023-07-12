# -*- coding: utf-8 -*-
{
    'name': "clinic appointment",
    'summary':"appointments  in clinic",

    # any module necessary for this one to work correctly
    'depends': ['base',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/assets.xml',
        'views/dashboard_views.xml',
        'views/expense.xml',
        'wizard/create_service.xml',
        'report/cashier_inv_report_temp.xml',
    ],
    'qweb': [
        'static/src/xml/template.xml'
    ],
}
