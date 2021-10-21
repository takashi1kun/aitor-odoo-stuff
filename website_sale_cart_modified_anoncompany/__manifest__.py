# -*- coding: utf-8 -*-
# (c) 2019 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2020 Aitor Rosell Torralba  <arosell@praxya.es>
# (c) 2021 Aitor Rosell Torralba  <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Super Carrito AnonBussiness por PRAXYA",

    'summary': """
        Este modulo modifica el comportamiento del carrito a los requerimientos de imporedcord""",

    'description': """
         Se modifica para que sea un solo paso de carrito a factura
         Se hace que los productos sugeridos sean mas bonitos
         Se añaden secciones tanto visualmente como logicamente
         Se ven solo los productos sugeridos de la ultima seccion
         Los productos sugeridos se abren en la misma pagina
         Se añade boton flotante redondo para facturar 
         Modulo hecho por Aitor Rosell Torralba <arosell@praxya.es>
    """,

    'author': "Praxya",
    'website': "https://www.praxya.com",
    'category': 'web',
    'version': '0.7',
    'depends': ['website_sale', 'sale_order_group_order_line', 'sale'],
    'data': [
        'views/views.xml',
        # 'views/confirmation_cart.xml',
        'views/templates.xml',
        'views/sale_order.xml',
        'views/cron.xml'
    ],
    'installable': True,
    'application': True,
}