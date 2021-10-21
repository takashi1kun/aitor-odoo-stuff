from odoo import api, fields, models

class ProjectProject(models.Model):
    _inherit = "project.project"

    coordinates = fields.Char("coordenadas")
    appnc_timesheet_ids = fields.One2many("appnc.timesheet","project_id","Partes Diarios Topografos")
    allowed_helper_ids = fields.Many2many('res.users',string="Ayudantes Permitidos")
    allowed_equipment_ids = fields.Many2many('appnc.equipment',
                                             string="Equipos Permitidos",
                                             default=lambda self: self._default_allowed_equipment_ids())
    allowed_productivity_fields_ids = fields.Many2many('appnc.productivity',
                                                       string="Campos Productividad Permitidos",
                                                       default=lambda self: self._default_allowed_productivity_fields_ids())

    @api.model
    def _default_allowed_equipment_ids(self):
        return self.env['appnc.equipment'].search([]).ids

    @api.model
    def _default_allowed_productivity_fields_ids(self):
        return self.env['appnc.productivity'].search([]).ids

    @api.multi
    def appnc_timesheets_action(self):
        self.ensure_one()
        return {
            'name': 'Partes diarios de Topografos de la obra '+self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'appnc.timesheet',
            'view_mode': 'tree',
            'view_type': 'form',
            'views': [(False, 'tree'), (False, 'form')],
            "domain": [["project_id", "=", self.id]],
            'target': 'current',
        }

class ProjectTask(models.Model):
    _inherit = "project.task"

    extra_allowed_helper_ids = fields.Many2many('res.users',string="Ayudantes Permitidos Extra")
    allowed_helper_ids = fields.Many2many('res.users', string="Ayudantes Permitidos por proyecto", related="project_id.allowed_helper_ids", readonly=True)
    allowed_equipment_ids = fields.Many2many('appnc.equipment',
                                             string="Equipos Permitidos",
                                             related="project_id.allowed_equipment_ids", readonly=True)
    allowed_productivity_fields_ids = fields.Many2many('appnc.productivity',
                                                       string="Campos Productividad Permitidos",
                                                       related="project_id.allowed_productivity_fields_ids",
                                                       readonly=True)
    extra_allowed_equipment_ids = fields.Many2many('appnc.equipment', string="Equipos Permitidos Extra")
    extra_allowed_productivity_fields_ids = fields.Many2many('appnc.productivity', string="Campos Productividad Permitidos Extra")

    @api.model
    def getHelpers(self):
        #extraHelpers = self.extra_allowed_helper_ids.filtered(lambda user: user.is_helper)
        #helpers = self.allowed_helper_ids.filtered(lambda user: user.is_helper)
        #helpers |= extraHelpers
        #if len(helpers.ids) == 0:
        #    helpers = self.env["res.users"].sudo().search([("is_helper","=", True)])
        helpers = self.env["res.users"].sudo().search([("is_helper", "=", True)])
        res = []
        for helper in helpers:
            res.append({
                "name": helper.name,
                "id": helper.id
            })
        return res

    @api.model
    def getEquipment(self):
        # equipments = self.allowed_equipment_ids | self.extra_allowed_equipment_ids | self.env["appnc.equipment"].search([])
        equipments = self.env["appnc.equipment"].search([])
        res = []
        for equipment in equipments:
            res.append(equipment.name)
        return res

    @api.model
    def getEquipmentIds(self):
        equipments = self.allowed_equipment_ids | self.extra_allowed_equipment_ids
        return equipments.ids

    @api.model
    def getProductivity(self):
        # productivity_fields = self.allowed_productivity_fields_ids | self.extra_allowed_productivity_fields_ids | self.env["appnc.productivity"].search([])
        productivity_fields = self.env["appnc.productivity"].search([])
        res = []
        for field in productivity_fields:
            res.append({
                "name": field.name,
                "type": field.type,
                "id": field.id
            })
        return res
