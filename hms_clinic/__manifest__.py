# -*- coding: utf-8 -*-
{
    'name': "clinic appointment",
    'summary':"appointment doctor in clinic",

    # any module necessary for this one to work correctly
    'depends': ['base','hms'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/appointment.xml',
    ],
}
