# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api

class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.model
    def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner):
        res = super(ProcurementRule, self)._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
        sale_order = self.env['sale.order'].sudo().search([('name','=',origin)], limit=1)
        is_internal_helper_line = product_id.helper_type == 'internal_helper'
        if sale_order.source_service:
            res['name'] = sale_order.PO_name if not is_internal_helper_line else "%s/Ayudante" % sale_order.PO_name
            res['source_service'] = sale_order.source_service.id
            res['date_order'] = sale_order.date_order
            res['SO_id'] = sale_order.id
            res['SO_ids'] = [(6,0 ,[sale_order.id])]
            res['driver_state'] = "not_set"
            res['service_driver_praxya'] = sale_order.service_driver_praxya
            res['internal_helper_purchase'] = is_internal_helper_line
            res['svroot_note'] = sale_order.svroot_note
        return res

    def _deal_with_suppliers_service_generator(self, values, product_id, res):
        line_type = values.get("line_type", "other")

        if line_type == "helper" and product_id.helper_type == 'internal_helper':  # Si es una linea de ayudante y el ayudante es interno, el proveedor tiene que ser el ayudante por defecto
            supplier_partner_id = self.default_helper_id
        else: # En cualquier otro caso, el proveedor es el conductor por defecto
            supplier_partner_id = self.default_driver_id

        if not supplier_partner_id:
            return res

        existent_seller_ids = product_id.seller_ids.filtered(lambda x: x.name.id == supplier_partner_id.id)
        existent_seller_id = existent_seller_ids[0] if len(existent_seller_ids) else False
        if not existent_seller_id:
            return res

        return existent_seller_id


    @property
    @api.model
    def default_driver_id(self):
        driver_id_number = self.get_param('default_driver_id', 0, int)
        driver_id = self.env["res.partner"].sudo().browse(driver_id_number)
        return driver_id

    @property
    @api.model
    def default_helper_id(self):
        helper_id_number = self.get_param('default_helper_id', 0, int)
        helper_id = self.env["res.partner"].sudo().browse(helper_id_number)
        return helper_id

    @api.model
    def get_param(self, value, default=False, parser=str):
        ParamModel = self.sudo().env['ir.config_parameter'].sudo()
        res = ParamModel.get_param(value, default)
        return parser(res) if res else res


    def _make_po_select_supplier(self, values, suppliers):
        """ Method intended to be overridden by customized modules to implement any logic in the
            selection of supplier.
        """
        res = super(ProcurementRule, self)._make_po_select_supplier(values, suppliers)
        product = self.env["product.template"].search([('name','=',values.get("move_dest_ids").name)], limit=1) if values.get("move_dest_ids", False) else False
        service_generator = values.get('group_id', self.env["procurement.group"]).serviceGenerator
        if service_generator and product:
            res = self._deal_with_suppliers_service_generator(values, product, res)
        return res

class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    @property
    @api.multi
    def serviceGenerator(self):
        if len(self) > 1:
            self.ensure_one()
        elif len(self) == 0:
            return False
        elif self.sale_id and self.sale_id.source_service:
            return self.sale_id.source_service
        else:
            return False