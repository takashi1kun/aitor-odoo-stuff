# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class StockMove(models.Model):
    _inherit = "stock.move"

    line_type = fields.Selection([
        ("primary", "Servicio Principal"),
        ("secondary", "Servicio Secundario"),
        ("helper", "Horas de Ayudante"),
        ("other", "Otros")
    ], string="Tipo", default='other')

    def _prepare_procurement_values(self):
        """ Prepare specific key for moves or other componenets that will be created from a procurement rule
        comming from a stock move. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        res = super(StockMove, self)._prepare_procurement_values()
        if self.sale_line_id:
            res.update({"line_type": self.sale_line_id.line_type})
            self.line_type = self.sale_line_id.line_type
        elif self.purchase_line_id:
            res.update({"line_type": self.purchase_line_id.line_type})
            self.line_type = self.purchase_line_id.line_type
        return res

class StockPickingOriginalDocument(models.Model):
    _inherit = 'stock.picking'
    source_service = fields.Many2one(comodel_name='sale.order.service.generator',string='Servicio Origen')
    driver_state = fields.Selection([
        ('no_driver', 'No Conductor'),
        ('not_set', 'Sin Asignar'),
        ('set', 'Asignado')
    ], compute="compute_driver", string="Estado Conductor", store=True)
    start_hour = fields.Float("Entrada")
    exit_hour = fields.Float("Salida")
    disable_night_shift = fields.Boolean("Turno de noche gratuito", default=False)
    driver_picking_type = fields.Selection([
        ('odoo_default', "Por defecto de Odoo"),
        ('driver', "De Conductor"),
        ('helper', "De Ayudante(Interno)")
    ], default='odoo_default', required=True, string="Tipo de albaran")
    driver_sale_picking_id = fields.Many2one("stock.picking")
    driver_purchase_picking_ids = fields.One2many("stock.picking", 'driver_sale_picking_id')

    unique_reference_code = fields.Char("Referencia Unica Conjunta", compute="_unique_reference_code_generator",
                                        store=True)

    real_client_id = fields.Many2one("res.partner",string="Cliente Servicio", compute="_compute_real_client_id", store=True,
        readonly=True, help="""Este es el cliente que contrato el servicio de este albaran.""")


    @api.multi
    @api.depends('source_service', 'driver_picking_type', 'source_service.cliente')
    def _compute_real_client_id(self):
        for this in self:
            if this.driver_picking_type != "odoo_default" and this.source_service and this.source_service.cliente:
                this.real_client_id = this.source_service.cliente.id
            else:
                this.real_client_id = False

    @property
    @api.multi
    def date_formatted_for_code(self):
        self.ensure_one()
        return datetime.strptime(self.scheduled_date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y/%m/%d')

    @api.multi
    @api.depends('source_service', 'scheduled_date', 'source_service.name')
    def _unique_reference_code_generator(self):
        for this in self:
            if this.source_service:
                this.unique_reference_code = "%s/%s" % (this.source_service.name, this.date_formatted_for_code)
            else:
                this.unique_reference_code = ""

    @api.multi
    @api.depends("partner_id")
    def compute_driver(self):
        conductor_defecto_id = int(self.sudo().env['ir.config_parameter'].sudo().get_param('default_driver_id'))
        for this in self:
            if this.partner_id.is_driver:
                this.driver_state = 'not_set' if this.partner_id.id == conductor_defecto_id else 'set'
            else:
                this.driver_state = 'no_driver'
