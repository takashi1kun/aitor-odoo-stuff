# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    line_type = fields.Selection([
        ("primary", "Servicio Principal"),
        ("secondary", "Servicio Secundario"),
        ("helper", "Horas de Ayudante"),
        ("other", "Otros")
    ], string="Tipo", default='other')

    custom_extra_discount = fields.Float("Descuento Personalizado", digits=dp.get_precision('Discount'), default=0.0)


    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id', 'custom_extra_discount')
    def _onchange_discount(self):
        if self.custom_extra_discount > 0.0:
            self.discount = self.custom_extra_discount
        else:
            return super(SaleOrderLine, self)._onchange_discount()


    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a procurement rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        res.update({"line_type": self.line_type})
        return res


class SaleOrderOriginalDocument(models.Model):
    _inherit = 'sale.order'
    source_service = fields.Many2one(comodel_name='sale.order.service.generator',string='Servicio Origen')
    week_day = fields.Char(string="Dia Semana")
    generated_id = fields.Integer(string="Indice")
    PO_name = fields.Char()
    PO_id = fields.Many2one("purchase.order")
    has_driver_assigned = fields.Many2one("res.partner", compute="compute_driver")
    driver = fields.Many2one("res.partner", compute="compute_driver", store=True)
    service_driver_praxya = fields.Selection([('ya','YA'),('fijo', 'FIJO'), ('planificado', 'PLANIFICADO')],
                               string='Tipo de Servicio', default='ya')
    svroot_note = fields.Html("Nota Generatriz", sanitize=False, sanitize_attributes=False, sanitize_tags=False, sanitize_style=False,
                       strip_style=False, strip_classes=False, related='source_service.note')
    driver_state = fields.Selection([
        ('no_purchase', 'Sin Compra'),
        ('no_driver', 'No Conductor'),
        ('not_set', 'Sin Asignar'),
        ('set', 'Asignado')
    ], compute="compute_driver", string="Estado Conductor", store=True)

    unique_reference_code = fields.Char("Referencia Unica Conjunta", compute="_unique_reference_code_generator",
                                        store=True)

    @property
    @api.multi
    def date_formatted_for_code(self):
        self.ensure_one()
        return datetime.strptime(self.date_order, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y/%m/%d')

    @api.multi
    @api.depends('source_service', 'date_order', 'source_service.name')
    def _unique_reference_code_generator(self):
        for this in self:
            if this.source_service:
                this.unique_reference_code = "%s/%s" % (this.source_service.name, this.date_formatted_for_code)
            else:
                this.unique_reference_code = ""

    @api.model
    def _search_driver(self, operator, value):
        return [
            ("PO_id.partner_id", operator, value),
            ("PO_id.partner_id.is_driver", "=", True)
        ] if value else [("PO_id.partner_id.is_driver", "=", False)]

    @api.multi
    @api.depends("PO_id", "PO_id.driver_state", "PO_id.partner_id", "PO_id.has_driver")
    def compute_driver(self):
        for this in self:
            if this.PO_id:
                this.driver_state = this.PO_id.driver_state
                if this.PO_id.has_driver:
                    this.driver = this.PO_id.partner_id.id
                else:
                    this.driver = False
            else:
                this.driver_state = "no_purchase"
                this.driver = False

