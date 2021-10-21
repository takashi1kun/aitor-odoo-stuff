from odoo import fields, models, api
import dateutil.parser
import datetime

class AppncTimesheet(models.Model):
    _name = "appnc.timesheet"
    _description = "Parte Diario Topógrafo"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc"

    name = fields.Char(compute='_getName')
    date = fields.Date(string='Fecha', index=True, default=fields.Date.context_today, track_visibility="always")
    user_id = fields.Many2one('res.users', string='Cartógrafo', index=True, track_visibility="always")
    task_id = fields.Many2one('project.task', string="Tarea", index=True, track_visbility="always")
    project_id = fields.Many2one('project.project', string='Obra', index=True, track_visibility="always", related="task_id.project_id")
    partner_id = fields.Many2one('res.partner', string='Cliente', related="project_id.partner_id", readonly=True, track_visibility="always")
    state = fields.Selection([
        ('new', 'Nuevo'),
        ('progress', 'En Progreso'),
        ('signed', 'Firmado'),
        ('deleted', 'Eliminado'),
        ('rectificationRequest', 'Rectificacion Solicitada')
        ], default="new", string='Estado', track_visibility="onchange")
    coordinates = fields.Char(string='Localización', related="project_id.coordinates", readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', related="user_id.company_id", readonly=True)
    equipment_ids = fields.Many2many("appnc.equipment", string="Equipos Usados")
    helper_line_ids = fields.One2many('appnc.timesheet.helper', 'parent_id', string='Lineas de Ayudante')
    time_field = fields.Float(string='Horas en campo')
    time_field_extra = fields.Float(string='Horas extra en campo')
    time_cabinet_extra = fields.Float(string='Horas extra en gabinete')
    equipment_gps = fields.Boolean(string='GPS')
    equipment_et = fields.Boolean(string='E.T.')
    consumption_stakes = fields.Integer(string='Estacas utilizadas')
    consumption_spray = fields.Integer(string='Espráis utilizados')
    clientrep_name = fields.Char(string='Nombre Representante cliente')
    clientrep_position = fields.Char(string='Posición Representante cliente')
    clientrep_dni = fields.Char(string='DNI Representante cliente')
    clientrep_email = fields.Char(string='Email Representante cliente')
    signature_surveyor = fields.Binary(string='Firma Topógrafo')
    signature_clientrep = fields.Binary(string='Firma Representante del Cliente')
    line_ids = fields.One2many('appnc.timesheet.line', 'parent_id', string='Campos Productividad')
    note = fields.Text(string="Nota")
    rectification_ids = fields.One2many("appnc.timesheet.rectification", "part_id", string="Solicitudes de Rectificacion")

    def _getName(self):
        self.name = self.user_id.display_name+" "+self.project_id.display_name+" "+datetime.datetime.strftime(self.date,'%d/%m/%Y')

    @api.multi
    def closePart(self):
        for this in self:
            self.state = "signed"
            self.user_id.AppSetting_activePart_id = False
            self.user_id.AppSetting_activeTask_id = False
            self.user_id.AppSetting_hasActiveTask = False

    @api.model
    def getEditData(self):
        return {
            "date": datetime.datetime.strptime(self.date.strftime('%d/%m/%Y'),'%d/%m/%Y').timestamp()*1000,
            "hoursField": self.floatToString(self.time_field),
            "hoursExtraField": self.floatToString(self.time_field_extra),
            "hoursGabinet": self.floatToString(self.time_cabinet_extra),
            "consumptionStakes": self.consumption_stakes,
            "consumptionSpray": self.consumption_spray,
            "note": self.note,
            "helperLines": self.getHelperLines(),
            "equipmentLines": self.getEquipmentLines(),
            "productivityLines": self.getProductivityLines()
        }

    @api.model
    def getHelperLines(self):
        res = []
        for line in self.helper_line_ids:
            res.append({
                "helper": {
                    "name": line.user_id.name,
                    "id": line.user_id.id,
                },
                "hoursField": self.floatToString(line.time_field),
                "hoursExtraField": self.floatToString(line.time_field_extra),
                "hoursGabinet": self.floatToString(line.time_cabinet_extra),
                "id": line.id
            })
        return res

    @staticmethod
    def floatToString(number):
        hour, minute = divmod(number, 1)
        minute *= 60
        strMin = str(int(minute))
        strHr = str(int(hour))
        if len(strMin) == 1:
            strMin = "0"+strMin
        if len(strHr) == 1:
            strHr = "0"+strHr
        result = '{}:{}'.format(strHr, strMin)
        return result

    @api.model
    def getProductivityLines(self):
        res = []
        for line in self.line_ids:
            res.append({
                "type":{
                    "name": line.field_id.name,
                    "type": line.field_id.type,
                    "id": line.field_id.id,
                },
                "data": line.data,
                "id": line.id
            })
        return res

    @api.model
    def getEquipmentLines(self):
        res = []
        for line in self.equipment_ids:
            res.append(line.name)
        return res



    @api.multi
    def aprove(self):
        for this in self:
            if this.state == "rectificationRequest":
                this.rectification_ids.aprove()

    @api.multi
    def deny(self):
        for this in self:
            if this.state == "rectificationRequest":
                this.rectification_ids.deny()

    @api.model
    def getHelpers(self):
        return self.task_id.getHelpers()

    @api.model
    def getEquipment(self):
        return self.task_id.getEquipment()

    @api.model
    def getProductivity(self):
        return self.task_id.getProductivity()


class AppncTimesheetRectification(models.Model):
    _name = "appnc.timesheet.rectification"
    _description = "Peticion Rectificacion Parte Topografo"
    _order = "date_requested desc"

    date_requested = fields.Datetime(string='Fecha de Solicitud', index=True, default=fields.Datetime.now(), readonly=True)
    date_decided = fields.Datetime(string='Fecha de Decision')
    user_id = fields.Many2one('res.users', string='Cartógrafo que ha solicitado rectificacion', index=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', related="user_id.company_id", readonly=True)
    part_id = fields.Many2one("appnc.timesheet", string="Parte", readonly=True)
    clientrep_name = fields.Char(string='Nombre Representante cliente', readonly=True)
    clientrep_position = fields.Char(string='Posición Representante cliente', readonly=True)
    clientrep_dni = fields.Char(string='DNI Representante cliente', readonly=True)
    clientrep_email = fields.Char(string='Email Representante cliente', readonly=True)
    clientrep_signature = fields.Binary(string='Firma Representante del Cliente', readonly=True)
    manager_id = fields.Many2one('res.users', string='Encargado que ha aceptado o denegado la solicitud')
    state = fields.Selection([
        ("requested", "Solicitado"),
        ("accepted", "Aprobado"),
        ("denied", "Denegado"),
        ("cancel", "Cancelado")
    ],"Estado")

    @api.multi
    def aprove(self):
        for this in self:
            if this.state == "requested":
                this.manager_id = self.env.user.id
                this.date_decided = fields.Datetime.now()
                this.state = "accepted"
                this.part_id.state = "progress"
                this.part_id.user_id.AppSetting_hasActiveTask = True
                this.part_id.user_id.AppSetting_activePart_id = this.part_id
                this.part_id.user_id.AppSetting_activeTask_id = this.part_id.task_id
                this.part_id.user_id.AppSetting_hasActiveRequest = False

    @api.multi
    def deny(self):
        for this in self:
            if this.state == "requested":
                this.manager_id = self.env.user.id
                this.date_decided = fields.Datetime.now()
                this.state = "denied"
                this.part_id.state = "signed"
                this.part_id.user_id.AppSetting_hasActiveRequest = False