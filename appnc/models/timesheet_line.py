from odoo import fields, models, api
import dateutil.parser

class AppncTimesheetLine(models.Model):
    _name="appnc.timesheet.line"

    parent_id = fields.Many2one('appnc.timesheet', string='Padre')
    field_id = fields.Many2one('appnc.productivity', string='Campo')
    company_id = fields.Many2one('res.company', string='Compañía', related="parent_id.company_id")
    user_id = fields.Many2one('res.users', string='Cartógrafo', related="parent_id.user_id")
    data = fields.Char(string='Valor')