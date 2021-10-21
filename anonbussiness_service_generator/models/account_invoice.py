# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import re
from typing import Iterable
#from collections import Iterable                            # < py38


def flatten(items):
    """Yield items from any nested iterable; see Reference."""
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x

regex_svroot_uncompiled = r"^(?:[a-zA-Z0-9]*)/(?:[0-9]*)/(?:[0-9]{4})/(?:0[1-9]|1[012])/(?:0[1-9]|[1-2][0-9]|3[01])$"
regex_svroot = re.compile(regex_svroot_uncompiled)


class SourceServiceWithInvoiceLine:
    def __init__(self, service, lines):
        self.source_service_id = service
        self.invoice_line_ids = lines



class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    is_transfer = fields.Boolean("Es de Transferencia Bancaria", default=False)
    iban_code = fields.Char(compute="_calc_iban")

    @api.multi
    @api.depends("bank_account_link", "fixed_journal_id", "fixed_journal_id.bank_account_id", "fixed_journal_id.bank_account_id.acc_number", "variable_journal_ids", "variable_journal_ids.bank_account_id", "variable_journal_ids.bank_account_id.acc_number")
    def _calc_iban(self):
        for this in self:
            if this.is_transfer:
                this.iban_code = (this.fixed_journal_id.bank_account_id.acc_number if this.fixed_journal_id and this.fixed_journal_id.bank_account_id else "") if this.bank_account_link == "fixed" else (this.mapped("variable_journal_ids.bank_account_id.acc_number") or [""])[0]
            else:
                this.iban_code = ""

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    unique_reference_code = fields.Char("Referencia Unica Conjunta", compute="_unique_reference_code_generator",
                                        store=True)
    sv_roots = fields.Many2many("sale.order.service.generator", compute="_get_sv_roots")


    @api.multi
    @api.depends('invoice_line_ids', 'unique_reference_code')
    def _get_sv_roots(self):
        for this in self:
            this.sv_roots = [(6,0, this.mapped("invoice_line_ids.sv_roots").ids)]

    @api.multi
    @api.depends('invoice_line_ids','invoice_line_ids.unique_reference_code')
    def _unique_reference_code_generator(self):
        for this in self:
            references = this.invoice_line_ids.filtered("unique_reference_code").mapped('unique_reference_code')
            if len(references) == 1:
                this.unique_reference_code = references[0]
            elif len(references) > 1:
                this.unique_reference_code = ", ".join(sorted(set(', '.join(references).split(", "))))
            else:
                this.unique_reference_code = ""

    @api.multi
    def get_lines_by_service(self):
        line_ids = self.mapped("invoice_line_ids")
        source_service_ids = self.mapped("sv_roots")
        unique_references = list(set(filter(lambda x: "/" in x , ', '.join(self.mapped('unique_reference_code')).split(', '))))
        res = list(map(lambda x: {
            'service': x,
            'is_extra':False,
            'line_ids': list(filter(lambda line: x.id in line.sv_roots.ids, line_ids)),
            'references': list(map(lambda z: {
                'reference': z,
                'line_ids': list(filter(lambda line: z in line.unique_reference_code, line_ids))
            },sorted(filter(lambda y: x.name in y,unique_references))))
        },source_service_ids))
        #res = list(map(lambda service: SourceServiceWithInvoiceLine(
        #        service=service,
        #        lines=map(lambda x:  ,line_ids.filtered(lambda line: service.id in line.sv_roots.ids))),
        #    source_service_ids))
        remaining_line_ids = self.env["account.invoice.line"].sudo().browse(
            list(
                set(line_ids.ids).difference(
                    set(
                        flatten(
                            map(lambda x: map(lambda y: map(lambda z: z.id, y["line_ids"]),x["references"]), res)
                        )
                    )
                )
            )
        ).exists()
        if remaining_line_ids:
            res.append({
                'service': False,
                'is_extra': True,
                'line_ids': remaining_line_ids,
                'references':[
                    {
                        'reference': 'Modificaciones Factura Manuales',
                        'line_ids': remaining_line_ids
                    }
                ]
            })
        return res

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    unique_reference_code = fields.Char("Referencia Unica Conjunta", compute="_unique_reference_code_generator",
                                        store=True)
    unique_reference_code_visual = fields.Char("Referencia Unica Conjunta", compute="_unique_reference_code_generator",
                                        inverse="_inverse_unique_reference_code")
    unique_reference_code_manual = fields.Char("Referencia Unica Conunta Manual", default="")
    sv_roots = fields.Many2many("sale.order.service.generator", compute="_get_sv_roots")
    is_reference_editable = fields.Boolean(compute="_unique_reference_code_generator", store=True)

    @api.onchange('unique_reference_code_visual')
    def _inverse_unique_reference_code(self):
        for this in self.filtered(lambda x: x.unique_reference_code_visual and len(x.unique_reference_codes_getter) == 0 and bool(regex_svroot.fullmatch(x.unique_reference_code_visual))):
            tentative_code = this.unique_reference_code_visual
            svroot_code = tentative_code[:-11]
            has_svroot = bool(self.env["sale.order.service.generator"].sudo().search([("name", "=", svroot_code)], limit=1, count=True))
            if has_svroot:
                this.unique_reference_code_manual = tentative_code

    @property
    @api.multi
    def sv_root_names(self):
        self.ensure_one()
        if self.unique_reference_code:
            return list(map(lambda y: y[:-11], filter(lambda x: "/" in x , self.unique_reference_code.split(', '))))
        else:
            return []

    @api.multi
    @api.depends('unique_reference_code')
    def _get_sv_roots(self):
        for this in self:
            this.sv_roots = [(6,0, self.env['sale.order.service.generator'].sudo().search([('name', 'in', this.sv_root_names)]).ids)]

    @property
    @api.multi
    def unique_reference_codes_getter(self):
        def filter_empty(a):
            if a:
                return True
            else:
                return False
        if len(self) >= 1:
            return list(filter(filter_empty, {
                    *self.mapped('sale_line_ids.order_id.unique_reference_code'),
                    *self.mapped('purchase_id.unique_reference_code')
                }))
        else:
            return []

    @api.multi
    @api.depends('sale_line_ids', 'purchase_id', 'sale_line_ids.order_id.unique_reference_code', 'purchase_id.unique_reference_code', 'unique_reference_code_manual')
    def _unique_reference_code_generator(self):
        for this in self:
            references = this.unique_reference_codes_getter
            this.is_reference_editable = not bool(len(references))
            if len(references) == 1:
                this.unique_reference_code = references[0]
                this.unique_reference_code_visual = this.unique_reference_code
            elif len(references) > 1:
                this.unique_reference_code = ", ".join(references)
                this.unique_reference_code_visual = this.unique_reference_code
            elif this.unique_reference_code_manual:
                this.unique_reference_code = this.unique_reference_code_manual
                this.unique_reference_code_visual = this.unique_reference_code_manual
            else:
                this.unique_reference_code = ""
                this.unique_reference_code_visual = ""

