# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import time

logger = logging.getLogger(__name__)

from datetime import datetime
from odoo import models, fields, api, http, exceptions
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT


class AnonBussinessAppModelLoginNotification(models.TransientModel):
    _name = "anonbussiness.app.model.login.notification"
    _description = "Enviar Notificacion"

    title = fields.Char("Titulo de la notificacion")
    message = fields.Text("Mensage de la notificacion")
    device_ids = fields.Many2many("anonbussiness.app.model.login")

    @api.multi
    def send_notification(self):
        for this in self:
            this.device_ids.filtered(lambda device: device.is_logged_in and device.last_logged_user and device.can_send_notifications).sendNotification(this.title, this.message)


class AnonBussinessAppModelLogin(models.Model):
    _name = "anonbussiness.app.model.login"
    _description = "Dispositivos registrados"

    company_id = fields.Many2one(
        comodel_name='res.company',
        related='last_logged_user.company_id'
    )
    name = fields.Char(string="Nombre", compute="_get_name",inverse='_inverse_name', search='_search_name',compute_sudo=True)
    device_code = fields.Char("ID de Dispositivo")
    users_ids = fields.Many2many("res.users", 'anonbussiness_app_login_device_users_rel', 'device_id', 'user_id', string="Usuarios")
    is_logged_in = fields.Boolean("Esta Identificado")
    last_logged_user = fields.Many2one("res.users", "Ultimo Usuario Logeado")
    last_device_identification = fields.Datetime("Ultima identificacion del dispositivo")
    last_user_identification = fields.Datetime("Ultima identificacion de usuario")
    user_notification_key = fields.Char()
    can_send_notifications = fields.Boolean(default=False)
    log_ids = fields.One2many("anonbussiness.app.model.login.log","device_id","Registro")

    @api.multi
    @api.depends("device_code")
    def _get_name(self):
        for this in self:
            this.name = this.device_code

    @api.multi
    def _inverse_name(self):
        for this in self:
            this.device_code = this.name if this.name else False

    def _search_name(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        return [('device_code', operator, value)]

    @api.multi
    def sendNotificationTest(self):
        for device in self:
            push_service = device.last_logged_user.company_id.push_service()
            if device.can_send_notifications and device.user_notification_key and device.is_logged_in:
                push_service.notify_single_device(
                    registration_id=str(device.user_notification_key),
                    message_title="testing_if_notifications_enabled",
                    message_body="testing_if_notifications_enabled"
                )

    @api.multi
    def sendNotification(self, title, message):
        notification_model = self.env["anonbussiness.app.notification"]
        for device in self:
            push_service = device.last_logged_user.company_id.push_service()
            if device.can_send_notifications and device.user_notification_key and device.is_logged_in:
                notification_model.newNotification(user=device.last_logged_user, title=title, body=message)
                push_service.notify_single_device(
                    registration_id=str(device.user_notification_key),
                    message_title=title,
                    message_body=message,
                    message_icon="%s/assets/icons/android-chrome-256x256.png" % str(device.last_logged_user.company_id.app_url),
                    click_action=str(device.last_logged_user.company_id.app_url)
                )

    def logoff(self):
        for this in self:
            this.is_logged_in = False

    @api.multi
    def sendManualNotification(self):
        model = 'anonbussiness.app.model.login.notification'
        view = self.env.ref('anonbussiness_app_api.view_anonbussiness_app_login_notification')
        wiz = self.env[model].create({'device_ids':[(6,0, self.ids)]})
        return {
            'name': "Enviar Notificacion",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': model,
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
        }

    @api.multi
    def logoutOtherDevicesSameUser(self):
        self.ensure_one()
        if self.is_logged_in:
            other_devices = self.sudo().search([
                ("id", "!=", self.id),
                ("last_logged_user", "=", self.last_logged_user.id),
                ("is_logged_in", "=", True)
            ])
            for device in other_devices:
                device.is_logged_in = False

    def loginuser(self):
        for this in self:
            this.is_logged_in = True
            today = datetime.today()
            this.last_user_identification = today
            this.last_device_identification = today
            this.logoutOtherDevicesSameUser()

    def logindevice(self):
        for this in self:
            this.last_device_identification = datetime.today()


class AnonBussinessAppModelLoginLog(models.Model):
    _name = "anonbussiness.app.model.login.log"
    _description = "Registro de Dispositivo"
    _order = "date desc"

    device_id = fields.Many2one("anonbussiness.app.model.login", "Dispositivo")
    user_id = fields.Many2one("res.users","Usuario")
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='user_id.company_id',
        string="Compañia",
        readonly=True
    )
    type = fields.Selection([
        ("login", "Identificacion"),
        ("first_login", "Primera Identificacion"),
        ("logout", "Cerrar Sesion"),
        ("conection", "Conexion"),
        ("notification_registered", "Notificaciones Activadas"),
        ("open_task", "Tarea Descargada"),
        ("end_task", "Tarea Finalizada"),
        ("incidence_task", "Tarea Incidentada")
    ], string="Tipo")
    is_conection_related= fields.Boolean("Tipo Conectividad", default=False)
    is_task_related = fields.Boolean("Tipo Tarea", default=False)
    date = fields.Datetime("Fecha", default=lambda self: fields.Datetime.now())
    related_task_id = fields.Many2one("project.task","Tarea Relacionada")
    has_gps_location = fields.Boolean("Tiene Localizacion GPS", default=False)
    gps_location_id = fields.Many2one("anonbussiness.app.model.login.log.gps", "Localizacion GPS")
    url = fields.Char("GPS URL", related="gps_location_id.name", readonly=True)


class AnonBussinessAppModelLoginLogGps(models.Model):
    _name = "anonbussiness.app.model.login.log.gps"
    _description = "Localizacion GPS"
    _order = "timestamp"

    log_id = fields.Many2one("anonbussiness.app.model.login.log")
    device_id = fields.Many2one(
        "anonbussiness.app.model.login",
        "Dispositivo",
        related='log_id.device_id',
        readonly=True
    )
    user_id = fields.Many2one(
        "res.users",
        "Usuario",
        related='log_id.user_id',
        readonly=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='log_id.company_id',
        string="Compañia",
        readonly=True
    )
    timestamp = fields.Float()
    accuracy = fields.Float()
    altitude = fields.Float()
    altitudeAccuracy = fields.Float()
    heading = fields.Float()
    latitude = fields.Float()
    longitude = fields.Float()
    speed = fields.Float()
    name = fields.Char("URL", compute="_compute_google_maps_url", readonly=True, store=True)

    @api.multi
    @api.depends("latitude", "longitude")
    def _compute_google_maps_url(self):
        for this in self:
            if bool(this.latitude) and bool(this.longitude):
                this.name = "https://www.google.com/maps/search/?api=1&query=%s,%s" % (this.latitude, this.longitude)
            else:
                this.name = ""

    @api.multi
    def getGpsDic(self, only_one=False):
        if only_one:
            self.ensure_one()
        elif len(self.ids) == 0:
            raise ValueError("Se necesita al menos un registro")
        res = list(map(lambda this: {
            "timestamp": this.timestamp or None,
            "coords": {
                "accuracy": this.accuracy or None,
                "altitude": this.altitude or None,
                "altitudeAccuracy": this.altitudeAccuracy or None,
                "heading": this.heading or None,
                "latitude": this.latitude or None,
                "longitude": this.longitude or None,
                "speed": this.speed or None
            }
        }, self))
        return res[0] if only_one else res

    @api.model
    def createGPS(self, gps_data, log_id):
        new_gps = self.sudo().create({
            "log_id": log_id.id,
            "timestamp": gps_data["timestamp"] or False,
            "accuracy": gps_data["coords"]["accuracy"] or False,
            "altitude": gps_data["coords"]["altitude"] or False,
            "altitudeAccuracy": gps_data["coords"]["altitudeAccuracy"] or False,
            "heading": gps_data["coords"]["heading"] or False,
            "latitude": gps_data["coords"]["latitude"] or False,
            "longitude": gps_data["coords"]["longitude"] or False,
            "speed": gps_data["coords"]["speed"] or False
        })
        return new_gps


class AnonBussinessAppNotification(models.Model):
    _name = "anonbussiness.app.notification"
    _description = "Notificacion"
    _order = "date desc"

    name = fields.Char("Titulo")
    body = fields.Text("Mensaje")
    readed = fields.Boolean("Leida")
    user_id = fields.Many2one("res.users", string="Usuario")
    date = fields.Datetime("Fecha")

    @api.model
    def getUserNotifications(self, user, query_number=0, limit=25):
        offset = limit * query_number
        if query_number != 0:
            non_readed_length = self.sudo().search([
                ("user_id", "=", user.id),
                ("readed", "=", False)
            ], count=True)
            offset = offset + non_readed_length
        allNotifications = self.sudo().search([
            ("user_id", "=", user.id)
        ], offset=offset, limit=limit)
        res = allNotifications.getNotificationData()
        non_readed = allNotifications.filtered(lambda x: not x.readed)
        for notif in non_readed:
            notif.readed = True
        return res

    @property
    def datetime(self):
        return datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT)

    @property
    def timestamp(self):
        return int((time.mktime(self.datetime.timetuple()) + self.datetime.microsecond/1000000.0)*1000)

    @api.multi
    def getNotificationData(self):
        return list(map(lambda this: {
            "title": this.name,
            "body": this.body,
            "readed": this.readed,
            "date": this.timestamp
        }, self))

    @api.model
    def newNotification(self, user, title, body=""):
        res = self.sudo().create({
            "name": title,
            "body": body,
            "readed": False,
            "user_id": user.id,
            "date": fields.Datetime.now()
        })
        return res

