# -*- coding: utf-8 -*-
# (c) 2020 Aitor Rosell Torralba <arosell@praxya.es>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Reports de trabajadores',
    'summary': "Añade nuevos modelo para los reports de trabajadores",
    'version': '11.0.2.',
    'author': 'Praxya',
    'website': 'http://www.praxya.com/',
    'license': 'AGPL-3',
    'category': 'Praxya custom',
    'depends': [
        'project',
        'hr',
        'hr_attendance',
        'hr_timesheet'
    ],
    'data': [
        'views/hr_attendance_month.xml',
        'reports/hr_attendance_month_report.xml'
    ],
    'installable': True,
}
