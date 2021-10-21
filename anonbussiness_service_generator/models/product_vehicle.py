# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta, date as datedate
from odoo.exceptions import UserError, ValidationError


class ProductVehicle(models.Model):
    _name = 'product.vehicle'
    _description = "Vehiculo"

    name = fields.Char("Nombre", required=True)

    is_ya = fields.Boolean("Hay YA", default=True, readonly=True)
    is_planificado = fields.Boolean("Hay Planificados")
    is_fijo = fields.Boolean("Hay Fijos")

    is_horas = fields.Boolean("Hay Horas")
    is_km = fields.Boolean("Hay Kilometros")
    is_jornadas = fields.Boolean("Hay Jornadas")
    is_direccion = fields.Boolean("Hay Direccion")

    category_id = fields.Many2one('product.category',"Categoria")
    product_tmpl_ids = fields.One2many('product.template', related="category_id.parent_id")