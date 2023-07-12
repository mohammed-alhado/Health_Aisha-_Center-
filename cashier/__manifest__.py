
{
    'name': 'Cashier',
    'version': '13.1.0',
    'category': 'Account',
    'author': 'ahmed yahia',
    'summary': 'pay patient invoices',
    'description': """ handle patient invoice
    """,
    'depends': ['base_setup','mail','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_view.xml',
        'views/payment_view.xml',
        'views/session_view.xml',
        'views/cheque_view.xml',
        'views/down_payment_view.xml',
        'wizard/payment_wizard.xml',
        'wizard/cheque_wizrad.xml',
        'wizard/refund.xml',
        'report/cashier_inv_report_temp.xml',
    ],
    'installable': True,  
    'application': True,
}
