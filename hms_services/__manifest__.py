# -*- coding: utf-8 -*-
{
    'name': "Services",

    # any module necessary for this one to work correctly
    'depends': ['base','hms'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/request_service.xml',
    ],
}
