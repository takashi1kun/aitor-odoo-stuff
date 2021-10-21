# -*- encoding: utf-8 -*-
from odoo import api, models, fields


class SaleOperations(models.Model):
    _inherit = "sale.operations"

    generator_id = fields.Many2one("sale.order.service.generator", "generatriz", copy=False)

    def read(self, fields=None, load='_classic_read'):
        res = super(SaleOperations, self).read(fields,load)
        return res