# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'GTS COA',
    'version' : '1.7',
    'summary': 'GTS COA',
    'author' : "Geo Technosoft",
    'sequence': 30,
    'description': """ Chart of Accounts with hierarchy.
This module create parent and child relation in account""",
    'category' : 'Accounting & Finance',
    'price': 14.99,
    'currency':'EUR',
#    'license': 'OPL-1',
    'website': 'www.geotechnosoft.com',
    'depends' : ['account', 'account_accountant', 'report_xlsx'],
    'data': [
        'views/account_account_view.xml',
        'wizard/account_chart_view.xml',
        'report/report_accountchart_report_xlsx.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
