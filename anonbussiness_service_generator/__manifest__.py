# -*- coding: utf-8 -*-
# (c) 2019 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Generador de Servicios AnonBussiness por PRAXYA",

    'summary': """
        Genera SO y PO segun los paramteros""",

    'author': "Praxya",
    "license": "AGPL-3",
    'website': "http://www.praxya.com",
    'category': 'Sale',
    'version': '0.4',
    'depends': ['sale',
                'product',
                'purchase',
                'stock',
                'sale_management',
                'partner-anonbussiness',
                'procurement_purchase_no_grouping_praxya',
                'sale_order_operations',
                'sale_order_dates',
                'account_payment_purchase',
                'account_payment_mode',
                'account_move_line_purchase_info',
                'account_move_line_stock_info',
                'purchase_batch_invoicing',
                'sale_minimum_quantity'
                ],
    'conflicts': ['wizard_conductores_producto_origen','invoice_reports' ],
    'data': [
        "security/security.xml",
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/config.xml',
        'views/product.xml',
        'views/service_generator.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'views/stock_picking.xml',
        'views/account_invoice.xml',
        'views/anonbussiness_festive_dates.xml',
        'reports/invoice_report.xml',
        'views/menu_items.xml',
        'wizard_views/wizard.xml',
        'views/sequences.xml'
    ],
    'installable': True,
    'application': True,
}