# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class AnonBussinessClientPortal(models.TransientModel):
    _name = "anonbussiness.client.portal"
    _description = 'Portal de cliente'

    display_name = fields.Char(
        "Nombre",
        compute="_compute_display_name",
        readonly=True,
        store=True
    )
    name = fields.Char("Nombre", default="Portal del Cliente")
    logo_img = fields.Binary("logo", computed="_compute_logo_img")
    current_user = fields.Many2one('res.users', 'Current User', default=lambda self: self.env.user)
    last_sale_order_ids = fields.Many2many("sale.order",string="Últimas Órdenes de Compra", default=lambda self: self._get_sale_orders())
    last_invoice_ids = fields.Many2many("account.invoice",string="Últimas Facturas", default=lambda self: self._get_invoices())
    last_document_ids = fields.Many2many("custody.document",string="Últimos Documentos", default=lambda self: self._get_documents())
    hider = fields.Boolean()
    view_more_sale = fields.Char(string="Ver más",
                                 default=lambda self: self._get_link(
                                     'sale.order',
                                     "anonbussiness_client_portal.action_anonbussiness_client_portal_my_orders",
                                     "anonbussiness_client_portal.client_portal_sale_menu"))
    view_more_invoice = fields.Char(string="Ver más",
                                 default=lambda self: self._get_link(
                                     'account.invoice',
                                     "anonbussiness_client_portal.action_anonbussiness_client_portal_my_invoices",
                                     "anonbussiness_client_portal.client_portal_invoice_all_invoices_menu"))
    view_more_document = fields.Char(string="Ver más",
                                 default=lambda self: self._get_link(
                                     'custody.document',
                                     "anonbussiness_client_portal.action_anonbussiness_client_portal_my_documents",
                                     "anonbussiness_client_portal.client_portal_custody_my_documents_menu"))

    @api.model
    def _get_link(self, model, action, menu):
        return "/web#menu_id=%s&action=%s&view_type=tree&model=%s" % (menu, action, model)

    @api.multi
    def open_action_documents(self):
        action = self.env.ref('anonbussiness_client_portal.client_portal_custody_my_documents_menu').read()[0]
        return action

    @property
    @api.multi
    def oldest_date(self):
        current_date = datetime.date.today()
        first_day = current_date.replace(day=1)
        first_day_odoo = fields.Date.from_string((first_day - relativedelta(months=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return first_day_odoo

    @property
    @api.multi
    def partner_id(self):
        return self.env.user.portal_user_parent_company_partner_id.id or -1

    @api.model
    def _get_sale_orders(self):
        return self.env["sale.order"].sudo().search([
                ("partner_id", "=", self.partner_id),
                ("state", "not in", ("draft","cancel","sent")),
                ("confirmation_date", ">=", str(self.oldest_date))
            ], limit=5, order="confirmation_date desc").ids

    @api.model
    def _get_invoices(self):
        return self.env["account.invoice"].search([
                ("partner_id", "=", self.partner_id),
                ("state", "in", ("open","paid")),
                ('is_invoice_current_month', '=', True)
            ], limit=5, order="date_invoice desc").ids

    @api.model
    def _get_documents(self):
        self.search_read()
        return self.env["custody.document"].search([
                ("owner_id", "=", self.partner_id),
                ("custodia_state", "in", ("almc","almc_digi")),
                ("fecha_inventario", ">=", str(self.oldest_date))
            ], limit=5, order="fecha_inventario desc").ids

    @api.multi
    @api.depends("current_user")
    def _compute_computed_ids(self):
        for this in self:
            partner_id = self.env.user.portal_user_parent_company_partner_id
            this.last_sale_order_ids = self.env["sale.order"].sudo().search([
                ("partner_id", "=", partner_id.id or -1),
                ("state", "not in", ("draft","cancel","sent")),
                ("confirmation_date", ">=", str(self.oldest_date))
            ], limit=5, order="confirmation_date").ids
            this.last_invoice_ids = self.env["account.invoice"].search([
                ("partner_id", "=", partner_id.id or -1),
                ("state", "in", ("open","paid")),
                ('is_invoice_current_month', '=', True)
            ], limit=5, order="date_invoice").ids
            this.last_document_ids = self.env["custody.document"].search([
                ("owner_id", "=", partner_id.id or -1),
                ("custodia_state", "in", ("almc","almc_digi")),
                ("fecha_inventario", ">=", str(self.oldest_date))
            ], limit=5, order="fecha_inventario").ids

    @api.multi
    def _compute_logo_img(self):
        for this in self:
            this.logo_img = False

    @api.multi
    def execute(self):
        print("hola")

    @api.multi
    def test_function(self):
        return "hola que tal"

    @api.depends()
    def _compute_display_name(self):
        for record in self:
            record.display_name = 'Portal del Cliente'

    @api.multi
    def name_get(self):
        """ name_get() -> [(id, name), ...]

        Returns a textual representation for the records in ``self``.
        By default this is the value of the ``display_name`` field.

        :return: list of pairs ``(id, text_repr)`` for each records
        :rtype: list(tuple)
        """
        ids = self.ids
        result = list(map(lambda x: (x, "Portal del Cliente"), ids))
        return result


