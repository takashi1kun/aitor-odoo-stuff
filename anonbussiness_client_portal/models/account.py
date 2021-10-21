# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from .portal_list import RenderPortalList


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    is_invoice_current_month = fields.Boolean(string="Es de este mes", compute="_calc_is_invoice_current_month", search='_search_is_invoice_current_month', compute_sudo=True)

    @api.multi
    def invoice_print_portal(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        # self.ensure_one()
        # self.sent = True
        return self.env.ref('account.account_invoices_without_payment').report_action(self)
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)

    @property
    @api.multi
    def is_current_month(self):
        self.ensure_one()
        if not self.date_invoice:
            return False
        current_date = datetime.date.today()
        first_day = current_date.replace(day=1)
        last_day = (first_day + relativedelta(months=+1)) - relativedelta(days=1)
        first_day_odoo = fields.Date.from_string((first_day - relativedelta(months=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        last_day_odoo = fields.Date.from_string(last_day.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return last_day_odoo >= self.date_invoice >= first_day_odoo

    @api.multi
    @api.depends('date_invoice')
    def _calc_is_invoice_current_month(self):
        for invoice in self:
            invoice.is_invoice_current_month = invoice.is_current_month

    @api.model
    def _search_is_invoice_current_month(self, operator, value):
        if operator in ["not like", "not ilike", "not", "!="]:
            value = not value

        current_date = datetime.date.today()
        first_day = current_date.replace(day=1)
        last_day = (first_day + relativedelta(months=+1)) - relativedelta(days=1)
        first_day_odoo = fields.Date.from_string((first_day - relativedelta(months=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        last_day_odoo = fields.Date.from_string(last_day.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return [
            '&',
                ('date_invoice', ">=", first_day_odoo),
                ('date_invoice', '<=', last_day_odoo)
        ] if value else [
            '|',
                ('date_invoice', "<", first_day_odoo),
                ('date_invoice', '>', last_day_odoo)
        ]

    @api.multi
    def render_portal_list(self):
        menu_id = self.env.ref('anonbussiness_client_portal.client_portal_invoice_all_invoices_menu').id
        action_id = self.env.ref('anonbussiness_client_portal.action_anonbussiness_client_portal_my_invoices').id
        view_type = "form"
        model = "account.invoice"
        url = "/web#menu_id=%s&action=%s&id=%s&view_type=%s&model=%s" % (menu_id, action_id, self.id, view_type, model)
        return RenderPortalList(name=self.number,url=url,id=self.id,model="account.invoice")

