from odoo import fields, models, api
import dateutil.parser

class AppncProductivity(models.Model):
    _name="appnc.productivity"

    name = fields.Char(string='Nombre')
    type = fields.Selection([
        ('text', 'Texto'),
        ('checkbox', 'Verdadero/Falso'),
        ('number', ' Numero sin decimales'),
        ('number', 'Numero con decimales')
        ],string='Tipo de campo')
    active = fields.Boolean(string='¿Activo?')