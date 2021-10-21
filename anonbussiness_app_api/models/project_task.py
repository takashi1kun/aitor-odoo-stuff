# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    tipo_servicio = fields.Selection(
        string="Tipo de servicio",
        related="project_id.tipo_servicio", store=True
    )
    app_task_type = fields.Integer(
        string="task_type_app",
        compute="get_task_type", store=True
    )

    app_service_type = fields.Char(
        string="service_type_app",
        compute="get_model_type_compute", store=True
    )

    albaran_owner_id = fields.Many2one(comodel_name='res.partner', string='Propietario', related="albaran_id.owner_id")
    project_priority = fields.Selection([
        ('0', 'Baja'),
        ('1', 'Normal'),
        ('2', 'Urgente'),
        ], related="project_id.priority")
    # task_has_saved_data_in_app = fields.Boolean("Tarea tiene datos guardados en APP", related="albaran_id.task_has_saved_data_in_app")

    @api.model
    def getTasksByUser(self):
        allowed_task_types = self.env["project.task.type"].search([
            ("show_in_app", "=", True)
        ])
        return self.search([
            "&",
                ("user_id", "=", self.env.user.id),
                ("app_service_type", "in", ["A", "B", "C", "D", "E"]),
                ("stage_id", "in", allowed_task_types.ids),
                ("incidencia", "=", False),
                ("albaran_id", "!=", False),
                "|",
                    ("linked", "=", False),
                    "&",
                        ("can_init_next_task", "=", True),
                        ("linked", "=", True)
        ])

    @api.multi
    def getFullDataAPP(self):
        self.ensure_one()
        stockPicking = self.albaran_id
        return stockPicking.getDataTabGeneralInformation()

    @api.multi
    def getTaskMinData(self):
        data = self.sudo().read([
            "id",
            "name",
            "project_id",
            "app_task_type",
            "tipo_tarea",
            "tipo_albaran",
            "tipo_servicio",
            "albaran_id",
            "albaran_owner_id",
            "partner_id",
            "priority",
            "project_priority"
        ])
        return list(map(lambda record: {
                "taskId": record["id"],
                "taskName": record["name"],
                "taskProjectName": record["project_id"][1] or '',
                "hasSavedData": False,
                "taskType": {
                    "id": record["app_task_type"],
                    "string": self.get_task_type_string_model(record["app_task_type"]),
                    "model": self.get_model_type_model(record["tipo_tarea"],record["tipo_albaran"],record["tipo_servicio"])
                },
                "taskClientName": record["albaran_owner_id"][1] if record["albaran_owner_id"] and record["albaran_owner_id"][1] else record["partner_id"][1] or '',
                "taskDataInvoiceName": record["albaran_id"][1] or '',
                "priority": int(record["priority"]) + (int(record["project_priority"])*10)
            }, data))
        #return list(map(lambda this: {
        #        "taskId": this.id,
        #        "taskName": this.name,
        #        "taskProjectName": this.project_id.name or '',
        #        "hasSavedData": this.albaran_id.task_has_saved_data_in_app,
        #        "taskType": {
        #            "id": this.app_task_type,
        #            "string": this.get_task_type_string(),
        #            "model": this.get_model_type()
        #        },
        #        "taskClientName": this.albaran_id.owner_id.name if this.albaran_id.owner_id and this.albaran_id.owner_id.name else this.partner_id.name or '',
        #        "taskDataInvoiceName": this.albaran_id.name or '',
        #        "priority": int(this.priority) + (int(this.project_id.priority)*10)
        #    }, self))

    @api.model
    def get_task_type_string_model(self, app_task_type=0):
        arr = [
            "",
            "Special",
            "Archivista Recogida",
            "Recepcion",
            "Extraccion Peticion",
            "Ubicacion Recogida",
            "Ubicacion Insercion",
            "Ubicacion Devolucion",
            "Transporte Recogida Almacenables",
            "Expedicion Peticion",
            "Preparacion Consumibles",
            "transporte entrega consumibles",
            "Transporte Recogida Consumibles",
            "Transporte Entrega almacenables"
        ]
        return arr[app_task_type]

    @api.multi
    def get_task_type_string(self):
        self.ensure_one()
        arr = [
            "",
            "Special",
            "Archivista Recogida",
            "Recepcion",
            "Extraccion Peticion",
            "Ubicacion Recogida",
            "Ubicacion Insercion",
            "Ubicacion Devolucion",
            "Transporte Recogida Almacenables",
            "Expedicion Peticion",
            "Preparacion Consumibles",
            "transporte entrega consumibles",
            "Transporte Recogida Consumibles",
            "Transporte Entrega almacenables"
        ]
        return arr[self.app_task_type]

    @api.multi
    def change_user_message(self):
        for this in self:
            if this.user_id and not this.get_model_type() == "ERROR":
                this.user_id.sendNotification(
                    title="Nueva Tarea Asignada",
                    message="La tarea %s le ha sido asignada, puede que no este lista para hacerse" % this.name
                )

    @api.multi
    def change_stage_message(self):
        allowed_task_types = self.env["project.task.type"].search([
            ("show_in_app", "=", True)
        ])
        for this in self:
            if this.user_id and (this.stage_id.id in allowed_task_types.ids):
                this.user_id.sendNotification(
                    title="Nueva Tarea Disponible",
                    message="La tarea %s esta ahora disponible para hacerse" % this.name
                )

    @api.multi
    def write(self, vals):
        res = super(ProjectTask, self).write(vals)
        if vals.get('user_id'):
            self.change_user_message()
        if vals.get('stage_id'):
            self.change_stage_message()
        return res

    @api.model
    def get_model_type_model(self, task_type="archivista", tipo_albaran="none", tipo_servicio="none"):
        if task_type in ("t_entrega", "material") or tipo_albaran == "consumible":
            return "A"
        elif task_type in ("t_recogida", "expedicion"):
            return "B"
        elif task_type == "ubicacion":
            return "C"
        elif task_type == "extraccion":
            return "D"
        elif task_type == "recepcion":
            return "E"
        elif task_type == "archivista" and tipo_servicio == "recogida":
            return "F"
        else:
            return "ERROR"

    @api.multi
    def get_model_type(self):
        self.ensure_one()
        task_type = self.tipo_tarea
        if task_type in ("t_entrega", "material") or self.tipo_albaran == "consumible":
            return "A"
        elif task_type in ("t_recogida", "expedicion"):
            return "B"
        elif task_type == "ubicacion":
            return "C"
        elif task_type == "extraccion":
            return "D"
        elif task_type == "recepcion":
            return "E"
        elif task_type == "archivista" and self.tipo_servicio == "recogida":
            return "F"
        else:
            return "ERROR"

    @api.multi
    @api.depends("tipo_tarea", "tipo_servicio")
    def get_model_type_compute(self):
        for this in self:
            this.app_service_type = this.get_model_type()

    @api.multi
    @api.depends("tipo_servicio", "tipo_albaran", "tipo_tarea", "stage_id", "project_id", "project_id.tipo_servicio")
    def get_task_type(self):
        dictionary = {
            'archivista|||archivista|||recogida': 2,  # Archivista Recogida
            'recepcion|||almacenable|||devolucion': 3,  # Recepcion
            'recepcion|||almacenable|||destruccion': 3,  # Recepcion
            'recepcion|||almacenable|||insercion': 3,  # Recepcion
            'recepcion|||almacenable|||recogida': 3,  # Recepcion
            'extraccion|||almacenable|||peticion': 4,  # Extraccion Peticion
            'ubicacion|||almacenable|||recogida': 5,  # Ubicacion Recogida
            'ubicacion|||almacenable|||insercion': 6,  # Ubicacion Insercion
            'ubicacion|||almacenable|||devolucion': 7,  # Ubicacion Devolucion
            't_recogida|||almacenable|||recogida': 8,  # Transporte Recogida Almacenables
            't_recogida|||almacenable|||devolucion': 8,  # Transporte Recogida Almacenables
            'expedicion|||almacenable|||peticion': 9,  # Expedicion Peticion
            'material|||consumible|||recogida': 10,  # Preparacion Consumibles
            't_entrega|||consumible|||recogida': 11,  # transporte entrega consumible
            't_recogida|||consumible|||insercion': 12,  # Transporte Recogida Consumibles
            't_entrega|||almacenable|||peticion': 13,  # Transporte Entrega almacenable
        }
        for this in self:
            search_string = "%s|||%s|||%s" % (this.tipo_tarea, this.tipo_albaran, this.tipo_servicio)
            this.app_task_type = dictionary.get(search_string, 0)


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    show_in_app = fields.Boolean("Disponible en la APP", default=False)
