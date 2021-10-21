# -*- encoding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    company_id = fields.Many2one('res.company', default=False, invisible=True)

    @api.model
    def _clear_all_company_ids(self):
        """
        Ran at module Installation from a post_init hook.
        Changes `company_id` to False in all ProductPricelists that have it setted to a non False value.
        :return:
        """
        pricelists_with_companies = self.sudo().search([
            ('company_id', '!=', False)
        ])
        if bool(len(pricelists_with_companies)):
            pricelists_with_companies.sudo().write({
                'company_id': False
            })

    @staticmethod
    def no_company(vals):
        """
        Takes a vals dictionary from a create or a write as attribute and sets the key company_id to False,
        wherever it was defined or not, this is done to clear posible company_id as well to prevent it from being set
        to a non False value.
        :param: vals: values dictionary from a create or a write method.
        :return: vals dictionary but with key company_id set to False.
        """
        vals["company_id"] = False
        return vals

    @api.multi
    def write(self, vals):
        return super(Pricelist, self).write(self.no_company(vals))

    @api.model
    def create(self, vals):
        return super(Pricelist, self).create(self.no_company(vals))
