import ast

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    taskStatesAllowedInApp = fields.Many2many('project.task.type',string="Estados de Tarea a mostrar en APP")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ids = self.env['ir.config_parameter'].sudo().get_param('appnc.taskStatesAllowedInApp')
        if bool(ids):
            res.update(
                taskStatesAllowedInApp=[(6, 0, ast.literal_eval(ids))] if ids else False,
            )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('appnc.taskStatesAllowedInApp', self.taskStatesAllowedInApp.ids)


class ResUsers(models.Model):
    _inherit = "res.users"

    AppSetting_hasActiveTask = fields.Boolean("Tiene Tarea Activa", default=False)
    AppSetting_hasActiveRequest = fields.Boolean("Tiene Modificacion Activa", default=False)
    AppSetting_activeTask_id = fields.Many2one("project.task", "Tarea Activa")
    AppSetting_activePart_id = fields.Many2one("appnc.timesheet", "Parte Activo")