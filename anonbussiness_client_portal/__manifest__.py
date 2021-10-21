# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Portal del Cliente",
    'summary': """
        Añade un portal del cliente
        """,
    'author': "Praxya",
    'website': "http://www.praxya.com",
    'category': 'web',
    'version': '0.7',
    'depends': [
        "custody_document_anonbussiness",
        "sale_service_anonbussiness",
        "sale_custom_anonbussiness",
        "stock_custom_anonbussiness",
        "anonbussiness_carga_almacen",
        "project_custom_anonbussiness",
        "account_custom_anonbussiness",
        "anonbussiness_update",
        "web"
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/groups.xml',
        'data/sequences.xml',
        'templates/widget_templates.xml',
        'templates/login.xml',
        'templates/assets.xml',
        'views/anonbussiness_client_portal.xml',
        'views/anonbussiness_portal_request.xml',
        'views/sale_order.xml',
        'views/res_users.xml',
        'views/account_invoice.xml',
        'views/custody_document.xml',
        'wizards/views/custom_search_document_wizard.xml',
        'wizards/views/portal_pricelist_recompute_wizard.xml',
        'views/url_action.xml',
        'views/menu_items.xml',
        'data/user_action.xml'
    ],
    "qweb": ["static/src/xml/portal_list.xml"],
    'installable': True,
    'application': True,
}
