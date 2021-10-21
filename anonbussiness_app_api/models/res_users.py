# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
logger = logging.getLogger(__name__)

from odoo import models, fields, api, http


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.multi
    def sendNotification(self, title, message):
        for user in self:
            self.env["anonbussiness.app.model.login"].sudo().search([
                ("last_logged_user", "=", user.id),
                ("is_logged_in", "=", True),
                ("can_send_notifications", "=", True)
            ]).sendNotification(title, message)

    device_ids = fields.Many2many("anonbussiness.app.model.login", 'anonbussiness_app_login_device_users_rel', 'user_id', 'device_id', string="Usuarios")
    app_log_ids = fields.One2many("anonbussiness.app.model.login.log", "user_id", "Registro")
    anonbussiness_app_setting_darkmode = fields.Boolean(default=False)
    anonbussiness_app_setting_initialscan = fields.Boolean(default=False)
    app_notifications = fields.One2many("anonbussiness.app.notification", "user_id", "Notificaciones de la APP")


