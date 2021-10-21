# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    line_type = fields.Selection([
        ("primary", "Servicio Principal"),
        ("secondary", "Servicio Secundario"),
        ("helper", "Horas de Ayudante"),
        ("other", "Otros")
    ], string="Tipo", default='other')


    @api.multi
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking=picking)
        if len(res):
            if self.move_dest_ids:
                self.line_type = self.move_dest_ids.line_type
                res[0].update({"line_type": self.move_dest_ids.line_type})
            else:
                res[0].update({"line_type": self.line_type})
        return res


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    source_service = fields.Many2one(comodel_name='sale.order.service.generator',string='Servicio Origen')
    has_driver = fields.Boolean("Cliente es Conductor", related="partner_id.is_driver")
    has_driver_str = fields.Char( string="🚚",compute="has_driver_str_compute")
    SO_id = fields.Many2one("sale.order")
    SO_ids = fields.One2many("sale.order", "PO_id")
    driver_state = fields.Selection([
            ('no_driver', 'No Conductor'),
            ('not_set', 'Sin Asignar'),
            ('set', 'Asignado')
        ], default="no_driver", string="Estado Conductor")

    svroot_note = fields.Html("Nota Generatriz", sanitize=False, sanitize_attributes=False, sanitize_tags=False,
                              sanitize_style=False, strip_style=False, strip_classes=False,
                              related='source_service.note')

    service_driver_praxya = fields.Selection([('ya','YA'),('fijo', 'FIJO'), ('planificado', 'PLANIFICADO')],
                               string='Tipo de Servicio', default='ya')

    internal_helper_purchase = fields.Boolean("Compra de ayudante interno", default=False)



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

    @property
    @api.multi
    def my_sale_order_id(self):
        self.ensure_one()
        return self.env['sale.order'].sudo().search([('name', '=', self.origin)], limit=1) if self.source_service and self.origin else self.env['sale.order']


    @api.multi
    @api.depends("has_driver","partner_id","source_service")
    def has_driver_str_compute(self):
        for this in self:
            this.has_driver_str = "🚚" if this.has_driver and this.source_service else ""

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        if self.source_service:
            sale_order = self.my_sale_order_id
            res = {
                **res,
                'source_service': self.source_service.id,
                'scheduled_date': self.date_order,
                'start_hour': self.source_service.start_hour,
                'exit_hour': self.source_service.finish_hour,
                'disable_night_shift': self.source_service.free_night_hours,
                'driver_picking_type': 'helper' if self.internal_helper_purchase else 'driver',
                'driver_sale_picking_id': sale_order.picking_ids[0].id if sale_order and sale_order.picking_ids and len(sale_order.picking_ids) > 0 else False
            }
        return res
