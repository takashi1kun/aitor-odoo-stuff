# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import odoo
from odoo.addons.website.controllers.main import Website
from odoo import http, _
from odoo.http import request


class ControllerTest(http.Controller):
    @http.route('/portal_client/render_list', type='json', auth="user")
    def portal_client_render_list(self):
        context = dict(request.env.context)
        model = context.get("model", False)
        ids = context.get("ids", False)
        if model and ids and model in ["sale.order", "account.invoice", "custody.document"] and type(ids) == list and len(ids):
            RealModel_ids = request.env[model].browse(ids)
            return http.request.env['ir.ui.view'].render_template('anonbussiness_client_portal.render_list_real', {'docs': RealModel_ids})
        else:
            return ""
        pass

    @http.route('/portal_client/get_service/<int:res_id>', type='http', auth="user")
    def get_service(self, res_id):
        pass

    @http.route('/portal_client/suggested_services', type='json', auth="user")
    def portal_client_suggested_services(self):
        #context = dict(request.env.context)
        user_id = request.env.user
        model = "product.template"
        RealModel_ids = user_id.portal_user_parent_company_partner_id.property_product_pricelist.mapped("item_ids.product_id.product_tmpl_id").filtered(lambda x: x.type == "service")
        return http.request.env['ir.ui.view'].render_template('anonbussiness_client_portal.render_suggested_services_real', {'docs': RealModel_ids})

