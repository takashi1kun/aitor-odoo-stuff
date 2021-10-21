# -*- coding: utf-8 -*-
# (c) 2019 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2020 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2021 Aitor Rosell Torralba  <arosell@praxya.es>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
from datetime import datetime
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo.http import request
# from odoo.tools.misc import profile

class WebsiteSaleCart(WebsiteSale):

    def get_cached_attribute_value_ids(self, product):
        return product.cache_atribute_value_ids

    def _calc_get_attribute_value_ids(self, product):
        """ list of selectable attributes of a product

        :return: list of product variant description
           (variant id, [visible attribute ids], variant price, variant sale price)
        """
        # product attributes with at least two choices
        quantity = product._context.get('quantity') or 1
        product = product.with_context(quantity=quantity)

        visible_attrs_ids = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id').ids
        to_currency = request.website.get_current_pricelist().currency_id
        attribute_value_ids = []
        for variant in product.product_variant_ids:
            if to_currency != product.currency_id:
                price = variant.currency_id.compute(variant.website_public_price, to_currency) / quantity
            else:
                price = variant.website_public_price / quantity
            visible_attribute_ids = [v.id for v in variant.attribute_value_ids if v.attribute_id.id in visible_attrs_ids]
            attribute_value_ids.append([variant.id, visible_attribute_ids, variant.website_price / quantity, price])
        return attribute_value_ids

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, access_token=None, revive='', **post):
        """
        Main cart management + abandoned cart revival
        access_token: Abandoned cart SO access token
        revive: Revival method when abandoned cart. Can be 'merge' or 'squash'
        """
        #t1 = datetime.now()
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                return request.render('website.404')
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session[
                'sale_order_id']):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session[
                'sale_order_id']:  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        if order:
            from_currency = order.company_id.currency_id
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: from_currency.compute(price, to_currency)
        else:
            compute_currency = lambda price: price

        values.update({
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
            'get_attribute_value_ids': self.get_cached_attribute_value_ids
        })
        if order:
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            #values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            # force no-cache so IE11 doesn't cache this XHR
            return self.generate_popover(order_id=order, cart_id=order.custom_cart_id)
        #t2 = datetime.now()
        #res = request.render("website_sale.cart", values, lazy=False)
        #t3 = datetime.now()
        #print("ALERTA ROJA: ")
        #print("Empieza funcion: ")
        #print(t1)
        #print("toda funcion hecha menos renderizar: ")
        #print(t2)
        #print("despues de renderizar: ")
        #print(t3)
        #print("Tiempo pasado antes de renderizar: ")
        #print(t2-t1)
        #print("Tiempo pasado renderizando: ")
        #print(t3-t2)
        #print("Tiempo pasado total: ")
        #print(t3-t1)
        #return res
        return request.render("website_sale.cart", values)

    def generate_popover(self, order_id, cart_id):
        values= {
            "cart_id": cart_id,
            "order": order_id
        }
        return request.render("website_sale_cart_modified_praxya.custom_popover_cart", values, headers={'Cache-Control': 'no-cache'})

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        cart_id = sale_order.custom_cart_id
        cart_id.sections_ids.sudo()._get_i_am_active()
        cart_id._cart_update(
            product_id_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            attributes=self._filter_attributes(**kw),
        )
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/section/change/<int:section_order_number>'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def section_change(self, section_order_number):
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        cart_id = sale_order.custom_cart_id
        if cart_id and section_order_number in cart_id.mapped("sections_ids.order"):
            section_id = cart_id.sections_ids.filtered(lambda s: s.order == section_order_number)
            if section_id:
                cart_id.sudo().write({"active_section_id": section_id[0].id})
                section_id.sudo()._get_i_am_active()
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/section/delete/<int:section_order_number>'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def section_delete(self, section_order_number):
        sale_order = request.website.sale_get_order(force_create=True)
        cart_id = sale_order.custom_cart_id
        cart_id.delete_section(int(section_order_number))
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/section/new'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def section_new(self):
        sale_order = request.website.sale_get_order(force_create=True)
        cart_id = sale_order.custom_cart_id
        if cart_id:
            order = cart_id.get_next_order()
            existing_sectionsids = cart_id.sections_ids.ids
            section_id = request.env['sale.order.cart.section'].sudo().create({
                "order": order,
                "name": "Grupo de marcaje "+str(order),
                "my_sale_cart_id": cart_id.id
            })
            existing_sectionsids.append(section_id.id)
            cart_id.active_section_id = section_id.id
            # cart_id.section_ids =  [(6,0, existing_sectionsids)]
            section_id.sudo()._get_i_am_active()
        return request.redirect("/shop")


    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True):
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            return {}
        cart_id = order.custom_cart_id
        cart_id.sections_ids.sudo()._get_i_am_active()
        # cart_id.sections_ids.sudo()._get_product_line_service_line_ids()
        if set_qty < 0:
            set_qty = 0
        line = cart_id._cart_update(
            product_id_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            line_id_id=line_id
        )
        if isinstance(line, int):
            value = {'line_id': line, 'quantity': 0}
        else:
            value = {'line_id': line.id, 'quantity': line.product_qty if line.product_qty >= 0 else 0}
        value['cart_quantity'] = order.cart_quantity
        # value = order._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty)

        #if not cart_id.mapped("sections_ids.line_ids.product_qty"):
            #request.website.sale_reset()
            #return value

        # order = request.website.sale_get_order()
        # value['cart_quantity'] = order.cart_quantity
        from_currency = order.company_id.currency_id
        to_currency = order.pricelist_id.currency_id

        if not display:
            return value
        suggested_products = cart_id.get_suggested_products()
        value['website_sale.cart_lines'] = request.env['ir.ui.view'].render_template("website_sale.cart_lines", {
            'website_sale_order': order,
            'compute_currency': lambda price: from_currency.compute(price, to_currency),
            'suggested_products': suggested_products,
            'get_attribute_value_ids': self.get_cached_attribute_value_ids
        })
        return value



    @http.route(['/shop/cart/new-inline-variant'], type='http', auth="public", methods=['POST'], website=True, sitemap=False)
    def new_inline_variant(self, product_id=0, **post):
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        cart_id = sale_order.custom_cart_id
        cart_id.sections_ids.sudo()._get_i_am_active()
        cart_id._cart_update(
            product_id_id=int(product_id),
            set_qty=1,
            attributes=self._filter_attributes(**post),
        )
        return request.redirect("/shop/cart")


    @http.route(['/shop/confirm_sale_lines'], type='http', auth="public", website=True, sitemap=False)
    def confirm_sale_lines(self, **post):
        order_id = request.website.sale_get_order()
        cart_id = order_id.custom_cart_id
        cart_id.generate_sale_order_lines()
        order_id._amount_all()
        lines = cart_id.mapped("sections_ids.line_ids")
        sections = cart_id.sections_ids
        lines.unlink()
        sections.unlink()
        cart_id.unlink()
        order_id.custom_cart_id = False
        order_id.is_cart_open = False
        # order_id.state = "sent"
        request.session['sale_order_id'] = None
        request.env.user.partner_id.last_website_so_id = False
        # sale_order = request.website.sale_get_order(force_create=True)
        return request.redirect("/shop")


    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def checkout(self, **post):
        order = request.website.sale_get_order()

        #redirection = self.checkout_redirection(order)
        #if redirection:
        #    return redirection

        #if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
        #    return request.redirect('/shop/address')

        #for f in self._get_mandatory_billing_fields():
        #    if not order.partner_id[f]:
        #        return request.redirect('/shop/address?partner_id=%d' % order.partner_id.id)

        # values = order.custom_cart_id.checkout_values()

        # values.update({'website_sale_order': order})

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("website_sale.confirmation",  {'order': order})

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, sitemap=False)
    def confirm_order(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        order.onchange_partner_shipping_id()
        order.order_line._compute_tax_id()
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=True)
        extra_step = request.env.ref('website_sale.extra_info_option')
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")

    @http.route(
        ['/shop/cart/notesave'], type='http', auth='public',
        methods=['POST'], website=True, csrf=False)
    def notesave(self, **post):
        order = request.website.sale_get_order()
        order.note = post.get("note")
        return request.redirect("/shop/cart")
