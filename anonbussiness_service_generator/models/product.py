# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class ProductTypeProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def recalculate_price_for_provider(self):
        for product in self:
            product_price = product.standard_price
            for seller in product.seller_ids:
                seller.price = product_price
                seller.min_qty = product.minimum_qty

    @api.multi
    def regenerate_providers(self):
        drivers = self.env["res.partner"].sudo().search([("is_driver", "=", True), ('supplier', '=', True)])
        for product in self:
            product_price = product.standard_price
            current_driver_ids = self.env["res.partner"]
            for seller in product.seller_ids:
                seller.price = product_price
                seller.min_qty = product.minimum_qty
                current_driver_ids |= seller.name
            for driver in drivers:
                if driver.id not in current_driver_ids.ids:
                    product.seller_ids.create({
                        "name": driver.id,
                        "product_name": product.name,
                        "min_qty": product.minimum_qty,
                        "price": product_price,
                        "company_id": product.company_id.id,
                        "currency_id": product.company_id.currency_id.id,
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "product_id": product.id,
                        "delay": 0
                    })

    @api.multi
    def param(self, param, is_float=False):
        val = self.sudo().env['ir.config_parameter'].sudo().get_param(param)
        if is_float:
            return float(val)
        else:
            return int(val)

    @property
    @api.multi
    def hr_uom(self):
        return self.env["product.product"].browse(self.param('hr_uom_id'))

    @property
    @api.multi
    def km_uom(self):
        return self.env["product.product"].browse(self.param('km_uom_id'))

    @property
    @api.multi
    def km_price_unit_sale(self):
        return self.km_price_unit()

    @property
    @api.multi
    def hr_price_unit_sale(self):
        return self.hr_price_unit()

    @property
    @api.multi
    def km_price_unit_purchase(self):
        return self.km_price_unit(price_type="standard_price")

    @property
    @api.multi
    def hr_price_unit_purchase(self):
        return self.hr_price_unit(price_type="standard_price")

    @api.multi
    def km_price_unit(self, price_type="list_price"):
        self.ensure_one()
        if self.service_type_praxya == "otro":
            return 0.0
        elif self.service_type_praxya == "ya" and self.uom_id.id == self.km_uom_id.id:
            return getattr(self, price_type)
        elif self.product_ya_km_id:
            return getattr(self.product_ya_km_id, price_type)
        else:
            raise ValueError(
                "El producto %s no tiene definido el producto equivalente de ya km, y no es un ya km el mismo, hay que configurar este valor para los kilometros extra" % self.name)

    @api.multi
    def hr_price_unit(self, price_type="list_price"):
        self.ensure_one()
        if self.service_type_praxya == "otro":
            return 0.0
        elif self.service_type_praxya == "ya" and self.uom_id.id == self.hr_uom_id.id:
            return getattr(self, price_type)
        elif self.product_ya_id:
            return getattr(self.product_ya_id, price_type)
        else:
            raise ValueError(
                "El producto %s no tiene definido el producto equivalente de ya horas, y no es un ya horas el mismo, hay que configurar este valor para los kilometros extra" % self.name)


class ProductTypeTemplate(models.Model):
    _inherit = "product.template"
    service_type_praxya = fields.Selection([('ya','YA'),('fijo', 'FIJO'), ('planificado', 'PLANIFICADO'),('otro','OTRO')],
                               string='Tipo de Servicio',default='otro')
    product_ya_km_id = fields.Many2one("product.product","Producto de Kilometros Extra")
    km_uom_id = fields.Many2one('product.uom', compute="get_values_hr_uom_id")
    product_ya_id = fields.Many2one("product.product","Producto de Horas Extra")
    hr_uom_id = fields.Many2one('product.uom', compute="get_values_hr_uom_id")
    is_product_vehicle = fields.Boolean("Es Producto un Vehiculo", compute="_compute_is_product_vehicle", search="_search_is_product_vehicle", inverse="_inverse_is_product_vehicle")
    helper_type = fields.Selection([('no_helper', 'No es un producto de tipo ayudante'),('internal_helper', 'Ayudante Interno'),('external_helper', 'Ayudante Externo')], "Configuracion Ayudante", default="no_helper", required=True)


    @api.multi
    def get_extra_hr_id(self):
        self.ensure_one()
        if self.service_type_praxya == 'ya' and self.uom_id.id == self.hr_uom.id:
            return self.product_variant_id
        elif self.service_type_praxya in ['ya', 'fijo', 'planificado'] and self.product_ya_id:
            return self.product_ya_id
        elif self.service_type_praxya  == 'otro' or not self.service_type_praxya:
            raise UserWarning("Se ha intentado coger el extra de hr de un producto invalido")
        else:
            raise UserWarning("No se ha configurado el extra de HR para producto %s" % self.name)

    @api.multi
    def get_extra_km_id(self):
        self.ensure_one()
        if self.service_type_praxya == 'ya' and self.uom_id.id == self.km_uom.id:
            return self.product_variant_id
        elif self.service_type_praxya in ['ya', 'fijo', 'planificado'] and self.product_ya_km_id:
            return self.product_ya_km_id
        elif self.service_type_praxya  == 'otro' or not self.service_type_praxya:
            raise UserWarning("Se ha intentado coger el extra de km de un producto invalido")
        else:
            raise UserWarning("No se ha configurado el extra de KM para producto %s" % self.name)


    @api.multi
    @api.depends("service_type_praxya")
    def _compute_is_product_vehicle(self):
        for this in self:
            this.is_product_vehicle = not this.service_type_praxya == 'otro'

    @api.multi
    def _inverse_is_product_vehicle(self):
        for this in self:
            if this.is_product_vehicle and this.service_type_praxya == 'otro':
                this.service_type_praxya = "ya"
            elif not this.is_product_vehicle and not this.service_type_praxya == 'otro':
                this.service_type_praxya = "otro"

    @api.model
    def _search_is_product_vehicle(self, operator, value):
        operator_positive = operator in ("=", "in", "like", "ilike")
        if value:
            operator = "!=" if operator_positive else "="
        else:
            operator = "=" if operator_positive else "!="
        return [('service_type_praxya', operator, 'otro')]

    @api.multi
    def param(self, param, is_float=False):
        val = self.sudo().env['ir.config_parameter'].sudo().get_param(param)
        if is_float:
            return float(val)
        else:
            return int(val)

    @property
    @api.multi
    def hr_uom(self):
        return self.env["product.uom"].browse(self.param('hr_uom_id'))

    @property
    @api.multi
    def km_uom(self):
        return self.env["product.uom"].browse(self.param('km_uom_id'))

    @property
    @api.multi
    def jornada_uom(self):
        return self.env["product.uom"].browse(self.param('jornada_uom_id'))


    @property
    @api.multi
    def km_price_unit_sale(self):
        return self.km_price_unit()

    @property
    @api.multi
    def hr_price_unit_sale(self):
        return self.hr_price_unit()

    @property
    @api.multi
    def km_price_unit_purchase(self):
        return self.km_price_unit(price_type="standard_price")

    @property
    @api.multi
    def hr_price_unit_purchase(self):
        return self.hr_price_unit(price_type="standard_price")

    @api.multi
    def km_price_unit(self, price_type="list_price"):
        self.ensure_one()
        if self.service_type_praxya == "otro":
            return 0.0
        elif self.service_type_praxya == "ya" and self.uom_id.id == self.km_uom_id.id:
            return getattr(self, price_type)
        elif self.product_ya_km_id:
            return getattr(self.product_ya_km_id, price_type)
        else:
            raise ValueError("El producto %s no tiene definido el producto equivalente de ya km, y no es un ya km el mismo, hay que configurar este valor para los kilometros extra" % self.name)

    @api.multi
    def hr_price_unit(self, price_type="list_price"):
        self.ensure_one()
        if self.service_type_praxya == "otro":
            return 0.0
        elif self.service_type_praxya == "ya" and self.uom_id.id == self.hr_uom_id.id:
            return getattr(self, price_type)
        elif self.product_ya_km_id:
            return getattr(self.product_ya_id, price_type)
        else:
            raise ValueError("El producto %s no tiene definido el producto equivalente de ya horas, y no es un ya horas el mismo, hay que configurar este valor para los kilometros extra" % self.name)

    @api.multi
    def recalculate_price_for_provider(self):
        for product in self:
            product_price = product.standard_price
            for seller in product.seller_ids:
                seller.price = product_price
                seller.min_qty = product.minimum_qty

    @api.multi
    def regenerate_providers(self):
        drivers = self.env["res.partner"].sudo().search([("is_driver","=", True),('supplier', '=', True)])
        for product in self:
            product_price = product.standard_price
            current_driver_ids = self.env["res.partner"]
            for seller in product.seller_ids:
                seller.price = product_price
                seller.min_qty = product.minimum_qty
                current_driver_ids |= seller.name
            for driver in drivers:
                if driver.id not in current_driver_ids.ids:
                    product.seller_ids.create({
                        "name": driver.id,
                        "product_name": product.name,
                        "min_qty": product.minimum_qty,
                        "price": product_price,
                        "company_id": product.company_id.id,
                        "currency_id": product.company_id.currency_id.id,
                        "product_tmpl_id": product.id,
                        "delay": 0
                    })

    @property
    @api.multi
    def category_ya_hr(self):
        self.ensure_one()
        if not self.categ_id:
            return False
        query = self.env["product.product"].search([
            ("categ_id", "=", self.categ_id.id),
            ("product_tmpl_id", "!=", self.id),
            ("service_type_praxya", "=", "ya"),
            ("uom_id", "=", self.hr_uom.id)
        ], limit=1)
        return query.id if query else False

    @property
    @api.multi
    def category_ya_km(self):
        self.ensure_one()
        if not self.categ_id:
            return False
        query = self.env["product.product"].search([
            ("categ_id", "=", self.categ_id.id),
            ("product_tmpl_id", "!=", self.id),
            ("service_type_praxya", "=", "ya"),
            ("uom_id", "=", self.km_uom.id)
        ], limit=1)
        return query.id if query else False

    @api.multi
    def autofill_ya_by_category(self):
        for product in self:
            if product.service_type_praxya == "ya" and product.uom_id.id != self.jornada_uom.id:
                if product.uom_id.id == self.km_uom.id and not product.product_ya_id:
                    product.product_ya_id = product.category_ya_hr
                elif product.uom_id.id == self.hr_uom.id and not product.product_ya_km_id:
                    product.product_ya_km_id = product.category_ya_km
            else:
                if not product.product_ya_id:
                    product.product_ya_id = product.category_ya_hr
                if not product.product_ya_km_id:
                    product.product_ya_km_id = product.category_ya_km




    @api.multi
    @api.depends('service_type_praxya', 'uom_id', 'product_ya_id', 'name', 'product_ya_km_id')
    def get_values_hr_uom_id(self):
        hr_uom_id = self.hr_uom
        km_uom_id = self.km_uom
        if hr_uom_id or km_uom_id:
            for this in self:
                if hr_uom_id:
                    this.hr_uom_id = hr_uom_id.id
                if km_uom_id:
                    this.km_uom_id = km_uom_id.id
