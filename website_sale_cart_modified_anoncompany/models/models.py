# -*- coding: utf-8 -*-
# (c) 2019 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2020 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2021 Aitor Rosell Torralba  <arosell@praxya.es>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import logging
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields, http
from odoo.http import request
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale
_logger = logging.getLogger(__name__)

def assign(value=False, number=1):
    return [value]*number

# class CrmControllerAitor(http.Controller):
#     @http.route(['/change_section/<int:number>/'], type='http', auth="public", methods=['GET'], website=True)
#     def change_section(self, number):
#         order = request.website.sale_get_order()
#         array = []
#         index = 0
#         array.append(request.env["sale.order.line"])
#         last = False
#         for producto in order.website_order_line:
#             if (producto.type == 'product' and not last):
#                 array[index] += producto
#             elif (producto.type == 'product' and last):
#                 index = index+1
#                 array.append(request.env["sale.order.line"])
#                 array[index] += producto
#                 last = False
#             elif (producto.type == 'service'):
#                 array[index] += producto
#                 last = True
#         array.append(array.pop(number-1))
#         arr = request.env["sale.order.line"]
#         for seccion in array:
#             for producto in seccion:
#                 arr += producto
#
#         order.id
#         order._changeOrder(order.id,arr)
#         print("El numero es:")
#         print("El numero es:")
#         return '<h1>hola</h1>'

class HashedProductTemplate:
    __slots__ = ('id', 'variant_ids', 'old_hash', 'new_hash')

    def __init__(self, product_data):
        self.id = product_data["id"]
        self.variant_ids = product_data["product_variant_ids"]
        self.old_hash = product_data["variant_ids_hash"]
        self.new_hash = hash(tuple(sorted(product_data["product_variant_ids"])))

    def needs_update(self):
        return not(self.old_hash == self.new_hash)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    _cache_atribute_value_ids_data = fields.Binary()
    _cache_atribute_value_set = fields.Boolean(default=False)

    #variant_ids_hash = fields.Integer(default=3527539)

    @api.model
    def cron_check_variant_changes(self):
        self.sudo().mass_calc_attribute_value_ids()
        #ProductTemplates = self.env["product.template"].sudo()
        #products = ProductTemplates.search([("type", "=", "service")]).read(["product_variant_ids", "variant_ids_hash"])
        #filtered_products = list(map(lambda x: x.id,filter(lambda x: x.needs_update(), map(HashedProductTemplate, products))))
        #if len(filtered_products):
        #    product_ids = ProductTemplates.browse(filtered_products)
        #    product_ids.write({
        #        '_cache_atribute_value_ids_data': False
        #    })

        #for product in filtered_products:
        #    product_id = ProductTemplates.browse([product.id])
        #    product_id.cache_atribute_value_ids = False
        #    product_id.variant_ids_hash = product.new_hash

    @api.model
    def cron_recalc_variants(self):
        pass
        #next_in_line = self.sudo().search([("type","=","service"),'|',("_cache_atribute_value_set", "=", False),("_cache_atribute_value_ids_data", "=", False)], limit=2)
        #if next_in_line:
        #    next_in_line.recalc_variant()

    @api.multi
    def recalc_variant(self):
        for this in self:
            this.cache_atribute_value_ids = this.calc_attribute_value_ids
            # this.variant_ids_hash = hash(tuple(sorted(this.product_variant_ids.ids)))

    @api.multi
    def reset_variant(self):
        for this in self:
            this.cache_atribute_value_ids = False
        self.sudo().mass_calc_attribute_value_ids()

    @api.model
    def mass_calc_attribute_value_ids(self):
        """ This is a method to very, VERY quickly preprocess a list of selectable attributes of all product.template
        of type 'service', this is so quick compared to the usual method that it is millions of times faster than usual
        This is not an exageration, usual way to preprocess would take a whole weekend, with this method it takes around
        ten seconds at most.
        There is a BUT in this, neither price or quantity is included in this calculation, this is due to quantity not
        being able to be preprocessed ahead of time and price being useless to compute without quantity. That being
        said, it is unneded to compute prices/quantity, because this is for services and services in anonbussiness does not
        need it's price to be computed for the ecommerce as it is invisible, so it is nill.
        There is a way it could be kind of precoumpted, we could only include the prices without the quantities, this
        would increase a bit the processing time but not by that much, then once only the prices relevant for calculations
        are save, another method would take these preprocessed values and only add the quantity and recompute the prices
        with the values saved, this would make it so that this is still blazing fast but quantities can be accounted for,
        but since these considerations are unnecesary due to the constrains of anonbussiness, this method stays the way it is
        without prices/quantities and only for services.
        """
        product_list = self.sudo().search([("type", "=", "service")]).read(["attribute_line_ids", "product_variant_ids"])
        variant_ids_set = set()
        line_ids_set = set()
        for product in product_list:
            for variant in product["product_variant_ids"]:
                variant_ids_set.add(variant)
            for line in product["attribute_line_ids"]:
                line_ids_set.add(line)
        variant_list = self.env["product.product"].sudo().browse(list(variant_ids_set)).read(["attribute_value_ids"])
        line_list = self.env["product.attribute.line"].sudo().browse(list(line_ids_set)).read(["value_ids", "attribute_id"])
        del line_ids_set
        del variant_ids_set
        variant_ids_dict = dict()
        line_ids_dict = dict()
        attribute_value_ids_set = set()
        for variant2 in variant_list:
            variant_ids_dict[variant2["id"]] = variant2
            for attr_var_id in variant2["attribute_value_ids"]:
                attribute_value_ids_set.add(attr_var_id)
        attribute_value_list = self.env["product.attribute.value"].sudo().browse(list(attribute_value_ids_set)).read(["attribute_id"])
        del attribute_value_ids_set
        del variant_list
        for line in line_list:
            line_ids_dict[line["id"]] = line
        del line_list
        attribute_value_dict = dict()
        for attribute_value in attribute_value_list:
            attribute_value_dict[attribute_value["id"]] = attribute_value["attribute_id"][0]
        del attribute_value_list
        for product in product_list:
            attribute_value_ids_res = []
            # visible_attrs_ids = list(map(lambda attr_id: attr_id["attribute_id"][0],filter(lambda att_id:  len(att_id["value_ids"]) > 1, self.env["product.attribute.line"].sudo().browse(product["attribute_line_ids"]).read(["value_ids", "attribute_id"]))))
            attribute_line_ids = map(lambda line_id: line_ids_dict[line_id], product["attribute_line_ids"])
            filtered_attribute_line_ids = filter(lambda att_id: len(att_id["value_ids"]) > 1, attribute_line_ids)
            visible_attrs_ids = list(map(lambda attr_id: attr_id["attribute_id"][0], filtered_attribute_line_ids))
            #attribute_value_ids_res = list(map(lambda variant: [variant["id"], list(filter(lambda x: attribute_value_dict[x] in visible_attrs_ids ,variant["attribute_value_ids"])), 1, 1],map(lambda variant_id: variant_ids_dict[variant_id], product["product_variant_ids"])))
            for variant in map(lambda variant_id: variant_ids_dict[variant_id], product["product_variant_ids"]):
                visible_attribute_ids = filter(lambda x: attribute_value_dict[x] in visible_attrs_ids ,variant["attribute_value_ids"])
                attribute_value_ids_res.append([variant["id"], list(visible_attribute_ids), 1, 1])
            self.sudo().browse([product["id"]]).sudo().write({
                '_cache_atribute_value_ids_data': json.dumps(attribute_value_ids_res).encode(),
                '_cache_atribute_value_set':True
            })


    @property
    @api.multi
    def calc_attribute_value_ids(self):
        """ list of selectable attributes of a product

        :return: list of product variant description
           (variant id, [visible attribute ids], variant price, variant sale price)
        """
        self.ensure_one()
        # product attributes with at least two choices
        quantity = 1
        product = self.with_context(quantity=quantity)

        visible_attrs_ids = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id').ids
        attribute_value_ids = []
        for variant in product.product_variant_ids:
            price = variant.website_public_price / quantity
            visible_attribute_ids = [v.id for v in variant.attribute_value_ids if v.attribute_id.id in visible_attrs_ids]
            attribute_value_ids.append([variant.id, visible_attribute_ids, variant.website_price / quantity, price])
        return attribute_value_ids

    @property
    @api.multi
    def cache_atribute_value_ids(self):
        self.ensure_one()
        if self._cache_atribute_value_set and self._cache_atribute_value_ids_data:
            res = self._cache_atribute_value_ids_data
            return json.loads(res.decode()) if res else False
        else:
            res = self.calc_attribute_value_ids
            self._cache_atribute_value_set = True
            self._cache_atribute_value_ids_data = res
            return res


    @cache_atribute_value_ids.setter
    @api.multi
    def cache_atribute_value_ids(self, value):
        self.ensure_one()
        if value:
            self.sudo().write({
                '_cache_atribute_value_ids_data': json.dumps(value).encode(),
                '_cache_atribute_value_set':True
            })
        else:
            self.sudo().write({
                '_cache_atribute_value_set': False,
                '_cache_atribute_value_ids_data': False
            })


class SaleWebCart(models.Model):
    _name = "sale.order.cart"

    sale_id = fields.Many2one("sale.order")
    company_id = fields.Many2one("res.company", related="sale_id.company_id")
    partner_id = fields.Many2one("res.partner", related="sale_id.partner_id")
    user_id = fields.Many2one("res.users", related="sale_id.user_id")

    sections_ids = fields.One2many(comodel_name="sale.order.cart.section", inverse_name="my_sale_cart_id")
    active_section_id = fields.Many2one(comodel_name="sale.order.cart.section")

    @property
    @api.multi
    def suggested_product_ids(self):
        self.ensure_one()
        if self.active_section_id:
            return self.active_section_id.suggested_product_ids
        else:
            return []

    @api.multi
    def delete_section(self, order_number):
        section_to_delete = self.sections_ids.filtered(lambda x: x.order == order_number)
        current_order = self.get_next_order() - 1
        if order_number < current_order:
            sections_to_change = self.sections_ids.filtered(lambda x: x.order > order_number)
            for section in sections_to_change:
                new_order = section.order - 1
                section.order = new_order
                section.name = "Grupo de marcaje "+str(new_order)
        section_to_delete.line_ids.sudo().unlink()
        section_to_delete.sudo().unlink()

    @api.multi
    def checkout_values(self):
        self.ensure_one()
        return {
            ""
        }

    @api.multi
    def generate_sale_order_lines(self):
        self.ensure_one()
        SaleOrderLineModel = self.env["sale.order.line"].sudo()
        line_ids = self.env["sale.order.line"]
        sale_product_line_ids = self.env["sale.order.line"]
        SectionModel = self.env["sale.layout_category"].sudo()
        ClicheSizeModel = self.env["sale.order.cliche.size"]
        sale_id = self.sale_id
        sections_ordered_ids = self.get_sections_ordered()
        sale_id.date_order, sale_id.commitment_date = assign(fields.Datetime.now(),2)
        sequence = 0
        for section_id in sections_ordered_ids:
            sale_section_id = SectionModel.search([("name", "=", str(section_id.order))], limit=1) or SectionModel.create({"name": str(section_id.order),"sequence": section_id.order,"subtotal": True,"pagebreak": True})
            section_sequence = 0
            section_id.product_line_ids = True
            section_id.service_line_ids = True
            cliches_ids = ClicheSizeModel.search([(
                "size",
                "in",
                section_id.service_line_ids.mapped(
                    'product_id.attribute_value_ids'
                ).filtered(
                    lambda x: x.attribute_id.name == "Cliche"
                ).mapped("name")
            )])
            cliche_field = [(6, 0, cliches_ids.ids)] if cliches_ids else False
            for product_line_id in section_id.product_line_ids:
                sequence = sequence + 1
                section_sequence = section_sequence + 1
                new_id = SaleOrderLineModel.create({
                    "sequence": sequence,
                    "layout_category_id": sale_section_id.id,
                    "layout_category_sequence":section_sequence,
                    "order_id": sale_id.id,
                    "product_id": product_line_id.product_id.id,
                    "product_uom_qty": product_line_id.product_qty,
                    "product_uom": product_line_id.product_id.uom_id.id,
                    "price_unit": product_line_id.product_id.lst_price,
                    "name": product_line_id.name,
                    "cliche_size": cliche_field
                })
                sale_product_line_ids |= new_id
                line_ids |= new_id
            for service_line_id in section_id.service_line_ids:
                sequence = sequence + 1
                section_sequence = section_sequence + 1
                cliche_name = service_line_id.mapped(
                    'product_id.attribute_value_ids'
                ).filtered(
                    lambda x: x.attribute_id.name == "Cliche"
                ).mapped("name")
                cliche_id = cliches_ids.filtered(lambda clich: clich.size in cliche_name) if cliche_name else False
                cliche_field2 = [(4, cliche_id.ids[0])] if cliche_id else False
                line_ids |= SaleOrderLineModel.create({
                    "sequence": sequence,
                    "layout_category_id": sale_section_id.id,
                    "layout_category_sequence": section_sequence,
                    "order_id": sale_id.id,
                    "product_id": service_line_id.product_id.id,
                    "product_uom_qty": service_line_id.product_qty,
                    "product_uom": service_line_id.product_id.uom_id.id,
                    "price_unit": service_line_id.product_id.lst_price,
                    "name": service_line_id.name,
                    "cliche_size": cliche_field2
                })
        # line_ids.product_id_change()
        line_ids._compute_tax_id()

    @api.multi
    def get_sections_ordered_not_active(self):
        self.ensure_one()
        res = self.sections_ids.ids[:]
        if res:
            res.remove(self.active_section_id.id)
        return self.sections_ids.browse(res)

    @api.multi
    def get_sections_ordered(self):
        self.ensure_one()
        # self.sections_ids._get_product_line_service_line_ids()
        return self.sections_ids.sorted("order")

    @api.multi
    def _cart_update(self, product_id_id=None, line_id_id=None, add_qty=0, set_qty=0, attributes=None,duplicate_lines=False, **kwargs):
        self.ensure_one()
        SaleWebCartSectionLineSudo = self.env['sale.order.cart.section.line'].sudo()
        had_line_id = bool(line_id_id)
        add_qty = int(add_qty or 0)
        set_qty = int(set_qty or 0)
        product_id_id = int(product_id_id or 0) or False
        line_id_id = int(line_id_id or 0) or False
        product_id = self.env["product.product"].sudo().search([('id', '=', product_id_id)], limit=1)
        line_id = SaleWebCartSectionLineSudo.search([('id', '=', line_id_id if line_id_id else 0)], limit=1)
        section_id = self.active_section_id if not line_id else line_id.section_id
        if not section_id and not self.active_section_id:
            order = self.get_next_order()
            section_id = self.env["sale.order.cart.section"].sudo().create({
                    "my_sale_cart_id": self.id,
                    "order": order,
                    "name": "Grupo de marcaje "+str(order)
                })
            self.active_section_id = section_id.id
        elif not section_id and self.active_section_id:
            section_id = self.active_section_id
        if not line_id:
            line_id = section_id.line_ids.filtered(lambda line: product_id.id == line.product_id.id)
        if line_id and product_id.id in line_id.mapped('product_id').ids and not duplicate_lines:
            if set_qty == 0 and add_qty == 0:
                lid = line_id.id
                line_id.sudo().unlink()
                if len(section_id.product_line_ids) == 0 and len(section_id.service_line_ids) > 0:
                    section_id.service_line_ids.unlink()
                return lid
            elif set_qty == 1 and product_id.type == "service" and not had_line_id:
                return self._cart_update(product_id.id, None, 0, 1, attributes, duplicate_lines=True)
            else:
                line_id.sudo().write({"product_qty": set_qty if set_qty else line_id.product_qty + add_qty})
        else:
            line_id = SaleWebCartSectionLineSudo.create({
                "name": self.sale_id._get_line_description(self.sale_id.id, product_id.id, attributes=attributes),
                "product_id": product_id.id,
                "section_id": section_id.id,
                "product_qty": set_qty or add_qty or 1,
                "product_type": "product" if product_id.type != "service" else "service"
            })
            section_id.sudo()._get_i_am_active()
            #section_id.sudo()._get_product_line_service_line_ids()
            if product_id.type != "service":
                #section_id.suggested_product_ids = True
                #section_id.product_line_ids = True
                suggested_ids = section_id.suggested_product_ids.ids
                ids_to_unlink = []
                for service in section_id.service_line_ids:
                    if service.product_id.product_tmpl_id.id not in suggested_ids:
                        ids_to_unlink.append((2, service.id))
                        # section_id.service_line_ids = False
                if bool(len(ids_to_unlink)):
                    section_id.line_ids = ids_to_unlink
            else:
                pass
                #section_id.service_line_ids = True
        return line_id

    @property
    @api.multi
    def should_button_be_shown(self):
        return self.mapped('sections_ids').get_do_i_have_products() if self.mapped('sections_ids') else False


    @api.multi
    def get_suggested_products(self):
        self.ensure_one()
        return self.active_section_id.suggested_product_ids if self.active_section_id else False



    @api.multi
    def get_next_order(self):
        self.ensure_one()
        order = self.sections_ids.mapped("order") or [0]
        return max(order)+1

    @api.multi
    def get_lines(self):
        self.ensure_one()
        sections = self.get_sections_ordered()
        lines = self.env["sale.order.cart.section.line"]
        for section in sections:
            for product in section.product_line_ids:
                lines |= product
            for service in section.service_line_ids:
                lines |= service
        return lines




    @api.multi
    def get_line_data(self):
        self.ensure_one()
        res = []
        for section in self.sections_ids.sorted("order"):
            for product in section.product_line_ids:
                res.append(product)
            for service in section.service_line_ids:
                res.append(service)
        return res

    @api.multi
    def get_cart_data(self):
        self.ensure_one()
        self.sections_ids._get_i_am_active()
        #self.sections_ids._get_product_line_service_line_ids()
        return list(map(lambda section: {
            "name": section.name,
            "products": list(map(lambda line: {
                "description": line.name,
                "product_image": line.product_id.image_variant,
                "product_name": line.product_id.name,
                "product_qty": line.product_qty,
                "product_price_unit": line.product_id.lst_price,
                "total": line.product_qty * line.product_id.lst_price
            }, section.product_line_ids)),
            "services": list(map(lambda line: {
                "description": line.name,
                "product_name": line.product_id.name,
                "product_qty": line.product_qty,
                "product_price_unit": line.product_id.lst_price,
                "total": line.product_qty * line.product_id.lst_price
            }, section.service_line_ids)),
            "active": section.active
        }, self.sections_ids.sorted("order")))

class SaleWebCartSection(models.Model):
    _name = "sale.order.cart.section"
    _order = "id asc, my_sale_cart_id asc, order asc"

    my_sale_cart_id = fields.Many2one(comodel_name="sale.order.cart", required=True)
    sale_id = fields.Many2one(comodel_name="sale.order", related="my_sale_cart_id.sale_id")
    company_id = fields.Many2one(comodel_name="res.company", related="my_sale_cart_id.company_id")
    partner_id = fields.Many2one(comodel_name="res.partner", related="my_sale_cart_id.partner_id")
    user_id = fields.Many2one(comodel_name="res.users", related="my_sale_cart_id.user_id")

    name = fields.Char()
    line_ids = fields.One2many("sale.order.cart.section.line", "section_id")

    # _product_line_ids = fields.Many2many("sale.order.cart.section.line", compute="_get_product_line_service_line_ids", store=True)
    # _service_line_ids = fields.Many2many("sale.order.cart.section.line", compute="_get_product_line_service_line_ids", store=True)

    cached_product_lines = fields.Many2many("sale.order.cart.section.line", relation="cache_product_lines_rel", column1="cart_section_ids", column2="cart_section_line_ids")
    cached_product_line_set = fields.Boolean(default=False)
    cached_service_lines = fields.Many2many("sale.order.cart.section.line", relation="cache_service_lines_rel", column1="cart_section_ids", column2="cart_section_line_ids")
    cached_service_line_set = fields.Boolean(default=False)

    _cached_suggested_product_ids = fields.Many2many("product.template")
    _cached_suggested_product_set = fields.Boolean(default=False)

    is_active = fields.Boolean(compute="_get_i_am_active", store=True)
    order = fields.Integer()

    @api.multi
    def only_10(self, thing):
        if len(thing) > 10:
            return thing[:10]
        else:
            return thing

    @property
    @api.multi
    def suggested_product_ids(self):
        self.ensure_one()
        return self.generate_suggested_product_for_this_category()
        if self._cached_suggested_product_set:
            # _logger.info("================================================")
            # _logger.info("==========SUGGESTED PRODUCT IDS START===========")
            # _logger.info(str(self._cached_suggested_product_ids.ids))
            # _logger.info("==========SUGGESTED PRODUCT IDS END=============")
            # _logger.info("================================================")
            # test_ids = self._cached_suggested_product_ids.ids
            # test_ids.remove(17531)
            # res = self.only_10(self._cached_suggested_product_ids.browse(test_ids))[0]
            # _logger.info(str(res.ids))
            return self._cached_suggested_product_ids
        else:
            new_ids = self.generate_suggested_product_for_this_category()
            self._cached_suggested_product_ids = [(6, 0, new_ids.ids)]
            self._cached_suggested_product_set = True
            # _logger.info("================================================")
            # _logger.info("==========SUGGESTED PRODUCT IDS START===========")
            # _logger.info(str(new_ids.ids))
            # _logger.info("==========SUGGESTED PRODUCT IDS END=============")
            # _logger.info("================================================")
            # test_ids = new_ids.ids
            # test_ids.remove(17531)
            # res = self.only_10(new_ids.browse(test_ids))[0]
            # _logger.info(str(res.ids))
            return new_ids
        
    @suggested_product_ids.setter
    @api.multi
    def suggested_product_ids(self, value):
        self.ensure_one()
        if value:
            value = value if type(value) != bool else self.generate_suggested_product_for_this_category()
            self._cached_suggested_product_ids = [(6, 0, value.ids)]
            self._cached_suggested_product_set = True
        else:
            self._cached_suggested_product_set = False

    @suggested_product_ids.deleter
    def suggested_product_ids(self):
        self.ensure_one()
        self._cached_suggested_product_ids = False
        self._cached_suggested_product_set = False



    @api.multi
    def get_do_i_have_products(self):
        return all(map(lambda section: bool(len(section.product_line_ids)), self))

    @api.multi
    def get_product_line_ids(self):
        return self.mapped('line_ids').filtered(lambda line: line.product_type == "product")

    @api.multi
    def get_service_line_ids(self):
        return self.mapped('line_ids').filtered(lambda line: line.product_type == "service")

    @property
    @api.multi
    def product_line_ids(self):
        return self.get_product_line_ids()
        if len(self.ids) >= 2:
            return self.get_product_line_ids()
        elif self.cached_product_line_set:
            return self.cached_product_lines
        else:
            res = self.get_product_line_ids()
            self.write({
                "cached_product_lines": [(6, 0, res.ids)],
                "cached_product_line_set": True
            })
            return res

    @product_line_ids.setter
    @api.multi
    def product_line_ids(self, value):
        self.ensure_one()
        if value:
            res = self.get_product_line_ids()
            self.write({
                "cached_product_lines": [(6, 0, res.ids)],
                "cached_product_line_set": True
            })
        else:
            self._cached_product_line_set = False


    @property
    @api.multi
    def service_line_ids(self):
        return self.get_service_line_ids()
        if len(self.ids) >= 2:
            return self.get_service_line_ids()
        elif self.cached_service_line_set:
            return self.cached_service_lines
        else:
            res = self.get_service_line_ids()
            self.write({
                "cached_service_lines": [(6, 0, res.ids)],
                "cached_service_line_set": True
            })
            return res

    @service_line_ids.setter
    @api.multi
    def service_line_ids(self, value):
        self.ensure_one()
        if value:
            res = self.get_service_line_ids()
            self.write({
                "cached_service_lines": [(6, 0, res.ids)],
                "cached_service_line_set": True
            })
        else:
            self._cached_service_line_set = False


    @api.multi
    def generate_suggested_product_for_this_category(self):
        # self._get_product_line_service_line_ids()
        line_ids = self.product_line_ids
        #current_product_ids = self.product_line_ids.mapped(lambda line: line.product_id.accessory_product_ids.ids)
        res = self.env['product.product']
        #accesory_product_ids = set.intersection(*[set(product.accessory_product_ids.ids) for product in current_product_ids])
        if line_ids:
            accesory_product_ids = list(
                set.intersection(
                    *map(lambda line: set(
                        line.product_id.accessory_product_ids.ids or []
                    ), line_ids)
                )
            )
            # for product in current_product_ids:
            #     for accesory in product.accessory_product_ids:
            #         add = True
            #         for product2 in current_product_ids:
            #             if product.id != product2.id and accesory.id not in product2.accessory_product_ids.ids:
            #                 add = False
            #                 break
            #         if add:
            #             res |= accesory.id
            # accesory_product_ids = self.product_line_ids.mapped("product_id.accessory_product_ids").filtered(
            #     lambda product: product.website_published and
            #                     product.type == 'service' and
            #                     product.id not in current_product_ids.ids
            #     ).mapped("product_tmpl_id")
            if len(accesory_product_ids):
                product_products = res.browse(accesory_product_ids).exists()
                if len(product_products):
                    product_templates = product_products.mapped("product_tmpl_id")
                    if len(product_templates):
                        sorting_keys = map(lambda x: {'id':x.id, 'sorted_key': x.default_code if x.default_code else "ZZZZZZZ"}, product_templates)
                        sorted_result = sorted(list(sorting_keys), key=lambda x: x['sorted_key'])
                        return self.env['product.template'].browse(item['id'] for item in sorted_result)
        return self.env['product.template']

    @api.multi
    def get_suggested_product_for_this_category(self):
        return self.suggested_product_ids

    @api.multi
    @api.depends("my_sale_cart_id", "my_sale_cart_id.active_section_id")
    def _get_i_am_active(self):
        for this in self:
            this.is_active = bool(this.id == this.my_sale_cart_id.active_section_id.id) if this.my_sale_cart_id and this.my_sale_cart_id.active_section_id else False

    # @api.multi
    # @api.depends("line_ids","line_ids.product_type")
    # def _get_product_line_service_line_ids(self):
    #     for this in self:
    #         this._product_line_ids = this.line_ids.filtered(lambda line: line.product_type == "product")
    #         this._service_line_ids = this.line_ids.filtered(lambda line: line.product_type == "service")



class SaleWebCartSectionLine(models.Model):
    _name = "sale.order.cart.section.line"

    _order = "id asc, section_id asc"

    name = fields.Char()
    section_id = fields.Many2one("sale.order.cart.section", required=True)
    sale_id = fields.Many2one("sale.order", related="section_id.sale_id")
    company_id = fields.Many2one("res.company", related="section_id.company_id")
    partner_id = fields.Many2one("res.partner", related="section_id.partner_id")
    user_id = fields.Many2one("res.users", related="section_id.user_id")

    product_type = fields.Selection([("product", "Producto"), ("service", "Servicio")], required=True)
    product_id = fields.Many2one("product.product", required=True)
    product_qty = fields.Integer(required=True)

    @api.multi
    def i_am_in_active_section(self):
        self.ensure_one()
        section_id = self.section_id
        my_sale_cart_id = section_id.my_sale_cart_id
        return section_id.id == my_sale_cart_id.active_section_id.id



class SaleOrder(models.Model):
    _inherit = "sale.order"
    # def _changeOrder(self,arr, id):
    #     order = self.search({"id":id})
    #     order.write({"website_order_line": arr})

    custom_cart_id = fields.Many2one("sale.order.cart")
    is_cart_open = fields.Boolean(default=False, string="Esta el carrito abierto")

    website_order_line = fields.One2many(
        'sale.order.line',
        compute='_compute_website_order_line',
        string='Order Lines displayed on Website',
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    website_order_cart_line = fields.One2many(
        'sale.order.cart.section.line',
        compute='_compute_website_order_line',
        string='Order Lines displayed on Website',
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )

    @api.multi
    @api.depends('custom_cart_id', 'website_order_cart_line.product_qty', 'website_order_cart_line.product_id')
    def _compute_cart_info(self):
        for order in self.filtered(lambda x: x.custom_cart_id):
            lines = order.custom_cart_id.mapped('sections_ids.line_ids')
            order.cart_quantity = int(sum(lines.mapped('product_qty')))
            order.only_services = all(l.product_id.type in ('service', 'digital') for l in lines)

    @api.one
    def _compute_website_order_line(self):
        self.website_order_cart_line = False if not self.custom_cart_id else self.custom_cart_id.get_lines()
        self.website_order_line = self.order_line

    @api.multi
    def _get_cliche(self, order_id, product_id, attributes=None):
        if not attributes:
            attributes = {}

        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product = self.env['product.product'].with_context(
            product_context).browse(product_id)

        cliche = ""
        for k, v in attributes.items():
            # attribute should be like 'attribute-48-1' where 48 is the product_id, 1 is the attribute_id and v is the attribute value
            attribute_value = self.env['product.attribute.value'].sudo().browse(
                int(v))
            if attribute_value and attribute_value.attribute_id.display_name.lower() == "cliche":
                cliche = attribute_value.name

        return cliche

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()
        cart_id = self.custom_cart_id
        line = cart_id._cart_update(
            product_id_id=int(product_id),
            line_id_id= int(line_id),
            add_qty=add_qty,
            set_qty=set_qty,
            attributes=attributes,
        )
        return {'line_id': line.id, 'quantity': line.product_qty}

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        for order in self:
            return order.custom_cart_id.get_suggested_products()

class Website(models.Model):
    _inherit = 'website'

    @api.multi
    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        res = super(Website, self).sale_get_order(force_create=force_create, code=code, update_pricelist=update_pricelist, force_pricelist=force_pricelist)
        if res:
            if len(res.order_line) > 0:
                res.is_cart_open = False
                new_sale_order_id = self.generate_new_order()
                request.session['sale_order_id'] = new_sale_order_id.id
                self.env.user.partner_id.last_website_so_id = new_sale_order_id.id
                res = new_sale_order_id
            if not res.custom_cart_id:
                cart_id = self.env["sale.order.cart"].sudo().create({
                    "sale_id": res.id
                })
                section_id = self.env["sale.order.cart.section"].sudo().create({
                    "my_sale_cart_id": cart_id.id,
                    "order": 1,
                    "name": "Grupo de marcaje 1"
                })
                cart_id.active_section_id = section_id.id
                section_id._get_i_am_active()
                res.sudo().write({
                    "custom_cart_id": cart_id.id,
                    "is_cart_open": True
                })
            if res.custom_cart_id and len(res.order_line) == 0 and not res.is_cart_open:
                res.sudo().write({
                    "is_cart_open": True
                })
        return res

    @api.multi
    def generate_new_order(self):
         pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id
         partner = self.env.user.partner_id
         pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
         so_data = self._prepare_sale_order_values(partner, pricelist)
         sale_order = self.env['sale.order'].with_context(force_company=request.website.company_id.id).sudo().create(
             so_data)
         # set fiscal position
         if request.website.partner_id.id != partner.id:
             sale_order.onchange_partner_shipping_id()
         else:  # For public user, fiscal position based on geolocation
             country_code = request.session['geoip'].get('country_code')
             if country_code:
                 country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                 fp_id = request.env['account.fiscal.position'].sudo().with_context(
                     force_company=request.website.company_id.id)._get_fpos_by_region(country_id)
                 sale_order.fiscal_position_id = fp_id
             else:
                 # if no geolocation, use the public user fp
                 sale_order.onchange_partner_shipping_id()

         return sale_order
