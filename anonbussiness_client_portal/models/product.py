# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
import hashlib


class ProductTemplate(models.Model):
    _inherit = "product.template"

    allowed_partner_ids = fields.Many2many(comodel_name="res.partner",relation="rel_portal_product_template_res_partner", column1="partner_id", column2="product_tmpl_id", compute="compute_allowed_partner_ids", compute_sudo=True, store=True)

    @api.multi
    @api.depends("item_ids", "item_ids.pricelist_id",
                 "item_ids.pricelist_id.partner_id","product_variant_ids.item_ids", "product_variant_ids.item_ids.pricelist_id",
                 "product_variant_ids.item_ids.pricelist_id.partner_id")
    def compute_allowed_partner_ids(self):
        for this in self:
            partner_ids = this.mapped("item_ids.pricelist_id.partner_id")
            partner_ids |= this.mapped("product_variant_ids.item_ids.pricelist_id.partner_id")
            this.allowed_partner_ids = [(6,0,partner_ids.ids)]
            current_ids = this.allowed_partner_ids.ids if this.allowed_partner_ids else []
            updates = []

            for partner_id in partner_ids:
                if partner_id.id not in current_ids:
                    updates.append((4, partner_id.id))
                elif partner_id.id in current_ids:
                    current_ids.remove(partner_id.id)

            for id_for_deletion in current_ids:
                updates.append((3, id_for_deletion))

            if len(updates):
                this.allowed_partner_ids = updates

    @property
    @api.multi
    def image_medium_url(self):
        """ Returns a local url that points to the image field of a given browse record. """
        self.ensure_one()
        if self.image_medium:
            record = self
            sudo_record = record.sudo()
            field = "image_medium"
            sha = hashlib.sha1(getattr(sudo_record, '__last_update').encode('utf-8')).hexdigest()[0:7]
            size = ''
            return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)
        else:
            return "/web/static/src/img/placeholder.png"
