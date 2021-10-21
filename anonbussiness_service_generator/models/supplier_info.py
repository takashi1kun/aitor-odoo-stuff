# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields

class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"
    delay = fields.Integer(
        'Delivery Lead Time', default=0, required=True,
        help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.")
