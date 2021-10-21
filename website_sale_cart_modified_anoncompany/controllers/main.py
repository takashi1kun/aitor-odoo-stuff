# -*- coding: utf-8 -*-
# (c) 2019 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2020 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2021 Aitor Rosell Torralba  <arosell@praxya.es>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging
from werkzeug.exceptions import NotFound

from odoo import http, tools, _
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

PPG = 20  # Products Per Page
PPR = 4   # Products Per Row

class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= PPR:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=PPG):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % PPR, pos // PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // PPR) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos // PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // PPR) + y2][(pos % PPR) + x2] = False
            self.table[pos // PPR][pos % PPR] = {
                'product': p, 'x': x, 'y': y,
                'class': " ".join(x.html_class for x in p.website_style_ids if x.html_class)
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // PPR))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows

class WebsiteSaleAnonBussiness(WebsiteSale):

    @http.route(['/shop/short_reference'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def short_reference_search(self, reference):
        if not reference or type(reference) != str:
            if type(reference) == int:
                reference = str(reference)
            else:
                return request.redirect("/shop?&search=Referencia%20Incorrecta")
        Products = request.env['product.template'].sudo()
        # First search if there is a short reference that is equal to the value, or it has variants with a seller reference that is equal
        short_referenece_search = Products.search([
            "&",
                ('website_published', "=", True),
                "|",
                    ("product_variant_ids.product_short_reference", "=", reference),
                    ('product_variant_ids.product_seller_reference', '=', reference)
        ], limit=1)
        # If there is not a short reference found, try to search a long reference equal to the value
        if not short_referenece_search:
            short_referenece_search = Products.search([
                "&",('website_published', "=", True),("default_code", "=", reference)
            ], limit=1)
            # If there is neither short or long reference equal to the value, search short references
            # that are similar to the value and get the first
            if not short_referenece_search:
                short_referenece_search = Products.search([
                    "&",
                        ('website_published', "=", True),
                        "|",
                            ("product_variant_ids.product_short_reference", "ilike", reference),
                            ('product_variant_ids.product_seller_reference', 'ilike', reference)
                ], limit=1)
                # If there is still nothing, search long references that are similar and get the first
                if not short_referenece_search:
                    short_referenece_search = Products.search([
                        "&",('website_published', "=", True),("default_code", "ilike", reference)
                    ], limit=1)
                    # If nothing works, redirect to a search with the value
                    if not short_referenece_search:
                        return request.redirect("/shop?&search=%s" % reference)
        # If there is a result, show the product page
        return request.redirect("/shop/product/%s" % slug(short_referenece_search))



    def _get_search_domain(self, search, category, attrib_values):
        domain = request.website.sale_product_domain()
        if search:
            for srch in search.split(" "):
                domain += [
                    '&',
                        ('website_published', "=", True),
                        '|',
                            '|',
                                '|',
                                    '|',
                                        ('name', 'ilike', srch),
                                        ('description', 'ilike', srch),
                                    ('description_sale', 'ilike', srch),
                                ('product_variant_ids.default_code', 'ilike', srch),
                            ('variant_seller_ids.product_code', 'ilike', srch)]

        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        return domain


    @http.route()
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        if category:
            category = request.env['product.public.category'].search(
                [('id', '=', int(category))], limit=1)
            if not category:
                raise NotFound()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in
                         attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        domain = self._get_search_domain(search, category,
                                         attrib_values)

        keep = QueryURL('/shop', category=category and int(category),
                        search=search, attrib=attrib_list,
                        order=post.get('order'))

        compute_currency, pricelist_context, pricelist = self._get_compute_currency_and_context()

        request.context = dict(request.context, pricelist=pricelist.id,
                               partner=request.env.user.partner_id)

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        categs = request.env['product.public.category'].search(
            [('parent_id', '=', False)])
        Product = request.env['product.template']

        parent_category_ids = []
        if category:
            url = "/shop/category/%s" % slug(category)
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(
                    current_category.parent_id.id)
                current_category = current_category.parent_id

        product_count = Product.search_count(domain)
        pager = request.website.pager(url=url, total=product_count,
                                      page=page, step=ppg, scope=7,
                                      url_args=post)
        products = Product.search(domain, limit=ppg,
                                  offset=pager['offset'],
                                  order=self._get_search_order(post))
        # ------------------------------- Modificado-----------------
        if len(domain) > 1:
            products_default_code = products.mapped('product_variant_ids.default_code')
            for product in products:
                products |= Product.search(
                    [('name', 'ilike', product.name)])
            products = products.filtered(
                lambda x: x.product_variant_ids[0].default_code in
                          products_default_code)

        # ---------------------

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            selected_products = Product.search(domain, limit=False)
            attributes = ProductAttribute.search([(
                                                  'attribute_line_ids.product_tmpl_id',
                                                  'in',
                                                  selected_products.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg),
            'rows': PPR,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'parent_category_ids': parent_category_ids,
        }
        if category:
            values['main_object'] = category
        return request.render("website_sale.products", values)