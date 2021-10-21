# -*- encoding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Disable Company in PriceList",
    "version": "11.0.0.1",
    "author": "Praxya",
    "website": "https://praxya.com",
    "license": "AGPL-3",
    "category": "Product",
    'summary': """
        Elimina el campo compañia en las tarifas para que las tarifas se puedan usar siempre en todas las compañias.
    """,
    "depends": [
        'product'
    ],
    "data": [
        'views/product_pricelist.xml'
    ],
    "installable": True,
    'post_init_hook': 'post_init_hook',
}
