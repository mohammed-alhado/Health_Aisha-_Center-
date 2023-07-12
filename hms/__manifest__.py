# -*- coding: utf-8 -*-
{
    'name': "hms Lab",
    # any module necessary for this one to work correctly
    'depends': ['base',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/labtest_view.xml',
        'views/lab_request_view.xml',
        'wizard/create_labtest.xml',
        'reports/lab_report.xml',
    ],
    
}
