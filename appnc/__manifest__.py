# Copyright 2020 Praxya - Aitor Rosell Torralba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Backend APP Cartografos",
    "summary": "Backend de la app de cartografos de anonbussiness",
    "author": "Praxya",
    'website': "https://www.praxya.com",
    'category': 'app',
    'version': '0.5',
    'depends': ['hr', 'project', 'googlemap', 'app_login_api','hr','hr_attendance'],
    'data': [
        'views/productivity.xml',
        'views/timesheet.xml',
        'views/project.xml',
        "views/config.xml",
        'security/ir.model.access.csv'
    ],
   'installable': True,
}