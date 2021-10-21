# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
logger = logging.getLogger(__name__)

from odoo import models, fields, api, http
from pyfcm import FCMNotification


class ResCompany(models.Model):
    _inherit = "res.company"

    push_service_object = False

    @api.multi
    def push_service(self):
        self.ensure_one()
        if not self.push_service_object:
            self.push_service_object = FCMNotification(api_key="ANONYM")
        return self.push_service_object

    app_api_key = fields.Char(default="ANONYM", string="API KEY de la App")
    app_private_key = fields.Char(default="ANONYM", string="PRIVATE KEY de la App")
    app_url = fields.Char(default="ANONYM", string="URL de la App")

