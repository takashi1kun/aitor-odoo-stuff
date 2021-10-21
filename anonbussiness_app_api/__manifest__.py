# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "API APP AnonBussiness",
    'summary': """
        API para la APP de AnonBussiness
        needs: pip install pyfcm
        """,
    'author': "Praxya",
    'website': "http://www.praxya.com",
    'category': 'API',
    'version': '0.8',
    'depends': ['web', 'anonbussiness_update', 'sale_service_anonbussiness', 'project_custom_anonbussiness'],
    "external_dependencies": {"python": ["pyfcm", "idna"]},
    'data': [
        'security/ir.model.access.csv',
        'views/anonbussiness_app_views.xml',
        'views/project_task_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': True,
    "post_init_hook": "post_init_hook",
}