# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta, date as datedate
from odoo.exceptions import UserError, ValidationError


class SaleOrderServiceGeneratorLine(models.Model):
    _name = 'sale.order.service.generator.line'
    _description = "Linea de Generador Raiz de Servicios"
    _order = "order_number asc, id desc"

    name = fields.Char(copy=False)
    order_number = fields.Integer(required=True)
    generator_id = fields.Many2one("sale.order.service.generator", "Generatriz", required=True)
    line_type = fields.Selection([
        ("primary", "Servicio Principal"),
        ("secondary", "Servicio Secundario"),
        ("helper", "Horas de Ayudante"),
        ("other", "Otros")
    ], "Tipo", required=True, default='other')
    product_id = fields.Many2one("product.product", "Producto")
    possible_product_ids = fields.Many2many("product.product", string="Productos posibles",
                                            compute="recompute_possible_products")
    product_qty = fields.Float("Cantidad")
    uom_id = fields.Many2one("product.uom", "Unidad Medida", related="product_id.uom_id")
    currency_id = fields.Many2one("res.currency", string="Moneda", related="product_id.currency_id")
    unit_price = fields.Monetary("Precio Unidad", currency_field="currency_id")
    company_id = fields.Many2one(
        'res.company',
        string='Comapañia',
        readonly=True,
        required=True,
        copy=False,
        index=True,
        default=lambda self: self.env.user.company_id.id)
    user_id = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        required=True,
        copy=False,
        string='Autor',
        index=True,
        default=lambda self: self.env.user,
    )
    creation_date = fields.Date(
        string='Fecha de Creacion',
        readonly=True,
        copy=False,
        index=True,
        default=datetime.today()
    )
    product_type = fields.Selection([("no", "No hay Producto Seleccionado"), ("hr", "Horas"), ("nohr", "no de horas")],
                                    default="no")

    block_product = fields.Boolean(default=False)

    can_be_deleted = fields.Boolean("Puede Ser Eliminado", compute="_calculate_can_be_deleted")

    @api.multi
    def change_service(self, service):
        for this in self:
            products_category_ids = self.env["product.product"].search([
                ('categ_id', '=', this.product_id.categ_id.id),
                ('service_type_praxya', '=', service),
                ('uom_id', '=', this.product_id.uom_id.id)
            ])
            if len(products_category_ids) != 0:
                this.product_id = products_category_ids[0].id
            else:
                raise ValidationError("No se puede cambiar el tipo de servicio correctamente dado que en las lineas no hay productos equivalentes para este servicio, por lo que tendra que hacer un servicio nuevo con el tipo que desea y cancelar este")

    @property
    @api.multi
    def other_line_ids(self):
        return self.browse(list(filter(lambda x: x not in self.ids, self.generator_id.line_ids.ids)))



    @api.multi
    def action_delete_line(self):
        other_line_ids = self.other_line_ids
        self._calculate_can_be_deleted()
        for this in self.filtered(lambda x: x.can_be_deleted):
            generator_id = this.generator_id
            extra_process = this.line_type == "primary"
            this.unlink()
            other_line_ids._calculate_can_be_deleted()
            if extra_process:
                generator_id.line_button_available = "primary"

    @api.multi
    @api.depends("generator_id.line_ids", "generator_id.state", "line_type", "product_id", "product_qty")
    def _calculate_can_be_deleted(self):
        for this in self:
            if this.generator_id.state == "draft":
                other_line_ids = this.other_line_ids
                if len(other_line_ids) != 0 and this.line_type == "primary":
                    this.can_be_deleted = False
                elif len(other_line_ids) == 0 and this.line_type == "primary":
                    this.can_be_deleted = True
                else:
                    this.can_be_deleted = True
            else:
                this.can_be_deleted = False


    @api.multi
    def generate_copy(self, generator_id):
        new_ids = self.env["sale.order.service.generator.line"]
        LineModel = self.env["sale.order.service.generator.line"]
        for this in self:
            new_ids |= LineModel.create({
                'generator_id': generator_id.id,
                'line_type': this.line_type,
                'product_id': this.product_id.id,
                'possible_product_ids': this.possible_product_ids.ids,
                'product_type': this.product_type,
                'block_product': this.block_product,
                'product_qty': this.product_qty,
                'unit_price': this.unit_price,
                'order_number': this.order_number,
                'name': this.name,
                'company_id': this.company_id,
                'user_id': this.user_id
            })
        new_ids.recompute_possible_products()
        return new_ids

    @property
    @api.multi
    def is_product_defined(self):
        return len(self.filtered(lambda x: not x.product_id)) == 0

    @api.multi
    @api.onchange("product_id")
    def _onchange_product_id(self):
        for this in self:
            this.unit_price = this.product_id.list_price
            if this.product_id:
                hr_uom_id = this.product_id.hr_uom_id
                if not this.product_qty:
                    this.product_qty = this.product_id.minimum_qty
                if this.uom_id.id == hr_uom_id.id:
                    this.product_type = "hr"
                else:
                    this.product_type = "nohr"
            else:
                this.product_type = "no"
                this.product_qty = 0

    @api.multi
    def block_primary(self):
        for this in self:
            if this.line_type == "primary":
                this.block_product = True
            else:
                this.block_product = False

    @api.multi
    @api.depends("line_type","generator_id","generator_id.service","generator_id.line_ids")
    def recompute_possible_products(self):
        for this in self:
            this.possible_product_ids = [(6, 0, this._compute_possible_products())]

    @api.multi
    def _compute_possible_products(self):
        products = self.env["product.product"]
        if self.line_type == "primary":
            res = products.search([
                ("service_type_praxya", "=", self.generator_id.service),
                ("helper_type", "=", "no_helper")
            ])
        elif self.line_type == "secondary":
            primary_product_id = self.generator_id.line_ids.filtered(lambda x: x.line_type == "primary")[0]
            res = products.search([
                ("service_type_praxya", "=", self.generator_id.service),
                ("categ_id", "=", primary_product_id.product_id.categ_id.id),
                ("uom_id", "!=", primary_product_id.product_id.uom_id.id),
                ("helper_type", "=", "no_helper"),
                ("id", "not in", self.generator_id.line_ids.filtered(
                    lambda l: l.id != self.id and l.line_type in ['primary', 'secondary']).mapped("product_id").ids)
            ])
        elif self.line_type == "helper":
            res = products.search([
                "&",
                    ("id", "not in", self.generator_id.line_ids.filtered(lambda l: l.id != self.id and l.line_type == 'helper').mapped("product_id").ids),
                    "|",
                        ("helper_type", "=", "external_helper"),
                        "&",
                            ("service_type_praxya", "!=", "otro"),
                            ("helper_type", "=", "internal_helper")
            ])
        else:
            res = products.search([("service_type_praxya", "=", "otro"),("helper_type", "=", "no_helper")])
        return res.ids

    @api.multi
    def generation_test(self):
        tipos = {
            "primary": "Primaria",
            "secondary": "Secundaria",
            "helper": "Ayudante",
            "other": "Otro"
        }
        errors = []
        for this in self:
            tipo = tipos.get(this.line_type) or ""

            if this.product_qty == 0:
                errors.append(
                    "La cantidad de la linea %s esta a 0, esto no esta permitido" % this.product_id.name or tipo
                )
            elif this.product_qty < 0:
                errors.append(
                    "La cantidad de la linea %s es inferior a 0, esto no esta permitido" % this.product_id.name or tipo
                )

            if not this.product_id:
                errors.append(
                    "Hay una linea de tipo %s sin producto asignado, esto no esta permitido" % tipo
                )
            elif this.product_id.categ_id.get_procured_purchase_grouping(company_id=this.company_id) != "sale_order":
                errors.append(
                    "La linea con producto %s esta asignada a una categoria que no agrupa por orden de venta, esto no esta permitido" % this.product_id.name
                )
            else:
                pass  # TODO: Hay que implementar una forma de comprobar las cantidades minimas, aunque aun no este asignado el proveedor real en este momento

            if this.unit_price == 0:
                errors.append(
                    "El precio de la linea %s esta a 0, esto no esta permitido" % this.product_id.name or tipo
                )
            elif this.unit_price < 0:
                errors.append(
                    "El precio de la linea %s es inferior a 0, esto no esta permitido" % this.product_id.name or tipo
                )

            if this.line_type == "primary":
                pass
            elif this.line_type == "secondary":
                pass
            elif this.line_type == "helper":
                pass
            else:
                pass
        return CustomErrorMessage(errors)


class CustomErrorMessage:
    def __init__(self, error_array=[]):
        self.has_errors = bool(len(error_array))
        if error_array:
            self.errors = error_array
