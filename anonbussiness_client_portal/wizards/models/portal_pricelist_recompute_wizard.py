# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.http import request


class PortalPricelistRecomputeWizard(models.TransientModel):
    _name = "portal.pricelist.recompute.wizard"

    def btn_recompute(self):
        module_obj = request.env['ir.module.module'].sudo()
        anonbussiness_client_portal = module_obj.search([('name', '=', 'anonbussiness_client_portal')])
        if anonbussiness_client_portal:
            anonbussiness_client_portal.button_immediate_upgrade()


