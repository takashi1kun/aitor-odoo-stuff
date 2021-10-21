# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from .portal_list import RenderPortalList


class SaleOrder(models.Model):
    _inherit = "sale.order"

    partner_portal_check_id = fields.Many2one('res.partner', compute="_compute_partner_portal_check_id", search="_search_partner_portal_check_id")
    is_origin_portal = fields.Boolean(default=False, string="El origen es el portal?")

    @property
    @api.multi
    def portal_request_id(self):
        self.ensure_one()
        if self.is_origin_portal:
            return self.env["portal.request"].sudo().search([('name', '=', self.origin)],limit=1).id
        else:
            return False

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        Portal = self.env["portal.request"]
        portal_ids = Portal.sudo().search([('code', 'in', list(set(self.filtered("is_origin_portal").mapped('origin'))))])
        if len(portal_ids):
            portal_ids.sudo().filtered(lambda x: x.state == "confirmed").sudo().write({
                'state': 'completed',
                'complete_date': fields.Datetime.now()
            })
        return res

    @api.multi
    @api.depends('partner_id')
    def _compute_partner_portal_check_id(self):
        for this in self:
            user_id = self.env.user
            partner_id = user_id.portal_user_parent_company_partner_id
            this.partner_portal_check_id = partner_id.id or False

    @api.model
    def _search_partner_portal_check_id(self, operator, value):
        user_id = self.env['res.users'].sudo().browse(value)
        partner_id = user_id.portal_user_parent_company_partner_id
        return [('partner_id', operator, partner_id.id)]

    @api.multi
    def render_portal_list(self):
        menu_id = self.env.ref('anonbussiness_client_portal.client_portal_sale_my_orders_menu').id
        action_id = self.env.ref('anonbussiness_client_portal.action_anonbussiness_client_portal_my_orders').id
        view_type = "form"
        model = "sale.order"
        url = "/web#menu_id=%s&action=%s&id=%s&view_type=%s&model=%s" % (menu_id, action_id, self.id, view_type, model)
        return RenderPortalList(name=self.name,url=url,id=self.id,model="sale.order")

    @api.model
    def create(self, vals):
        origin = vals.get('origin', False)
        if bool(origin):
            portal_request = self.env['portal.request'].search([('code', '=', origin)])
            vals.update({'is_origin_portal': bool(portal_request), 'note': portal_request.note})
        res = super(SaleOrder, self).create(vals)
        return res


class SaleService(models.Model):
    _inherit = "sale.service"

    is_origin_portal = fields.Boolean()

    @api.model
    def create(self, vals):
        sale_id = vals.get('sale_id', False)
        if bool(sale_id):
            sale = self.env['sale.order'].browse(sale_id)
            vals.update({'is_origin_portal': sale.is_origin_portal})
            if bool(sale.is_origin_portal):
                document_id = vals.get('document_id', False)
                document = self.env['custody.document'].browse(document_id)
                vals.update({
                    'anyo': document.year_desde,
                    'descripcion': document.tramo_desde,
                    'referencia': False,
                })
        res = super(SaleService, self).create(vals)
        return res

