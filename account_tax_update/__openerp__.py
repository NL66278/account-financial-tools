# -*- coding: utf-8 -*-
# Copyright 2012-2018 Therp BV <https://therp.nl>.
# Copyright 2013 Camptocamp SA.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Update tax wizard",
    "version": "8.0.1.0.45",
    "author": "Therp BV, Camptocamp SA,Odoo Community Association (OCA)",
    "category": 'Base',
    'complexity': "normal",
    "description": """
    """,
    'images': [
        'images/update_tax.png',
    ],
    'depends': [
        'account',
    ],
    'data': [
        'views/account_tax.xml',
        'views/update_tax_config.xml',
        'security/ir.model.access.csv',
    ],
    "license": 'AGPL-3',
    "installable": True,
}
