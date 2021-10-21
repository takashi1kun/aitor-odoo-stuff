from odoo import fields, models, api
import dateutil.parser

class AppncTimesheetHelper(models.Model):
    _name="appnc.timesheet.helper"

    user_id = fields.Many2one('res.users', string='Nombre Ayudante')
    parent_id = fields.Many2one('appnc.timesheet', string='Padre')
    company_id = fields.Many2one('res.company', string='Compañía', related="parent_id.company_id")
    time_field = fields.Float(string='Horas en campo')
    time_field_extra = fields.Float(string='Horas extra en campo')
    time_cabinet_extra = fields.Float(string='Horas extra en gabinete')


class ResUsers(models.Model):
    _inherit = "res.users"

    is_helper = fields.Boolean(string="Es ayudante")