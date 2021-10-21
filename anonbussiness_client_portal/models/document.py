# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from .portal_list import RenderPortalList


class CustodyDocument(models.Model):
    _inherit = "custody.document"

    @api.multi
    def render_portal_list(self):
        menu_id = self.env.ref('anonbussiness_client_portal.client_portal_custody_my_documents_menu').id
        action_id = self.env.ref('anonbussiness_client_portal.action_anonbussiness_client_portal_my_documents').id
        view_type = "tree"
        model = "custody.document"
        url = "/web#menu_id=%s&action=%s&id=%s&view_type=%s&model=%s" % (menu_id, action_id, self.id, view_type, model)
        return RenderPortalList(name=self.name,url=url,id=self.id,model="custody.document")



