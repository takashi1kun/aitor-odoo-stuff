from odoo import fields, models, api


class AppncEquipment (models.Model):
    _name = 'appnc.equipment'
    _description = 'Equipos'

    name = fields.Char(string="Nombre")
    


