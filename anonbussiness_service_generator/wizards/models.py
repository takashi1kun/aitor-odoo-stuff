# -*- coding: utf-8 -*-




from odoo import models, fields, api
from datetime import datetime


def is_a_in_list_b(a, b):
    return not set(a).isdisjoint(b)

class ServiceGeneratorAssignmentWizard(models.TransientModel):
    _name = "service.generator.assignment.wizard"

    is_helper_assignment = fields.Boolean("Asignando Ayudante?", default=False)

    conductor = fields.Many2one('res.partner', required=True, string='Conductor')
    ayudante = fields.Many2one('res.partner', string='Ayudante')
    documento_origen = fields.Many2one('sale.order.service.generator', required=True, string='Documento Origen')
    documentos_compra_sin_filtrar = fields.Many2many('purchase.order', 'name', string='Documentos de Compra')
    documentos_compra = fields.One2many('purchase.order', 'name', string='Documentos de Compra',
                                        compute="get_documentos_compra")
    readonly_origen = fields.Boolean(default=False)
    busqueda_avanzada = fields.Boolean(string="Busqueda Avanzada", default=False)
    busqueda_avanzada_semana_lunes = fields.Boolean(string="L", default=True)
    busqueda_avanzada_semana_martes = fields.Boolean(string="Ma", default=True)
    busqueda_avanzada_semana_miercoles = fields.Boolean(string="Mi", default=True)
    busqueda_avanzada_semana_jueves = fields.Boolean(string="J", default=True)
    busqueda_avanzada_semana_viernes = fields.Boolean(string="V", default=True)
    busqueda_avanzada_semana_sabado = fields.Boolean(string="S", default=True)
    busqueda_avanzada_semana_domingo = fields.Boolean(string="D", default=True)
    busqueda_avanzada_semana_todos = fields.Boolean(string="T", default=True)
    busqueda_avanzada_fecha_desde = fields.Date(string="Desde")
    busqueda_avanzada_fecha_hasta = fields.Date(string="Hasta")
    busqueda_avanzada_solo_sin_asignar = fields.Boolean(string="Solo sin Asignar", default=False)


    @api.onchange('ayudante')
    def update_driver_and_helper(self):
        self.conductor = self.ayudante.id

    @property
    @api.multi
    def all_week(self):
        self.ensure_one()
        return (
                    self.busqueda_avanzada_semana_lunes and
                    self.busqueda_avanzada_semana_martes and
                    self.busqueda_avanzada_semana_jueves and
                    self.busqueda_avanzada_semana_viernes and
                    self.busqueda_avanzada_semana_miercoles and
                    self.busqueda_avanzada_semana_sabado and
                    self.busqueda_avanzada_semana_domingo
                )

    @all_week.setter
    @api.multi
    def all_week(self, value):
        self.ensure_one()
        self.busqueda_avanzada_semana_lunes = value
        self.busqueda_avanzada_semana_martes = value
        self.busqueda_avanzada_semana_jueves = value
        self.busqueda_avanzada_semana_viernes = value
        self.busqueda_avanzada_semana_miercoles = value
        self.busqueda_avanzada_semana_sabado = value
        self.busqueda_avanzada_semana_domingo = value

    @api.multi
    @api.onchange(
        'busqueda_avanzada_semana_lunes',
        'busqueda_avanzada_semana_martes',
        'busqueda_avanzada_semana_miercoles',
        'busqueda_avanzada_semana_jueves',
        'busqueda_avanzada_semana_viernes',
        'busqueda_avanzada_semana_sabado',
        'busqueda_avanzada_semana_domingo'
    )
    def unselect_all(self):
        for this in self:
            this.busqueda_avanzada_semana_todos = this.all_week

    @api.multi
    @api.onchange('busqueda_avanzada_semana_todos')
    def select_all(self):
        for this in self:
            if this.busqueda_avanzada_semana_todos: # Si seleccionas que seleccione todos
                this.all_week = True
            elif this.all_week: # Si des-seleccionas que seleccione todos, y estan todos seleccionados al mismo tiempo
                this.all_week = False

    @property
    @api.multi
    def advance_search_domains(self):
        self.ensure_one()
        res = []
        if self.busqueda_avanzada:
            if self.busqueda_avanzada_solo_sin_asignar:
                res.append(('driver_state', '!=', 'set'))
            if self.busqueda_avanzada_fecha_desde:
                desde = "%s 00:00:00" % self.busqueda_avanzada_fecha_desde
                res.append(('date_planned', '>=', desde))
            if self.busqueda_avanzada_fecha_hasta:
                hasta = "%s 23:59:59" % self.busqueda_avanzada_fecha_hasta
                res.append(('date_planned', '<=', hasta))
        return res

    @api.multi
    def filter_po(self, order_id):
        self.ensure_one()
        if self.busqueda_avanzada:
            weekday_filter = [
                self.busqueda_avanzada_semana_lunes,
                self.busqueda_avanzada_semana_martes,
                self.busqueda_avanzada_semana_miercoles,
                self.busqueda_avanzada_semana_jueves,
                self.busqueda_avanzada_semana_viernes,
                self.busqueda_avanzada_semana_sabado,
                self.busqueda_avanzada_semana_domingo
            ]
            weekday = fields.Datetime.from_string(order_id.date_planned).weekday()
            if not weekday_filter[weekday]:
                return False
        if not (order_id.state == 'draft'):
            picking_states = order_id.mapped('picking_ids.state')
            invalid_states = ('done', 'cancel')
            if any(filter(lambda picking_state: picking_state in invalid_states, picking_states)):
                return False
        return True

    @api.multi
    @api.depends(
        'documentos_compra_sin_filtrar',
        'busqueda_avanzada_semana_lunes',
        'busqueda_avanzada_semana_martes',
        'busqueda_avanzada_semana_miercoles',
        'busqueda_avanzada_semana_jueves',
        'busqueda_avanzada_semana_viernes',
        'busqueda_avanzada_semana_sabado',
        'busqueda_avanzada_semana_domingo'
    )
    def get_documentos_compra(self):
        for this in self:
            result = this.documentos_compra_sin_filtrar.filtered(lambda POrder: this.filter_po(POrder))
            this.documentos_compra = [(6,0,result.ids)]


    @api.onchange(
        'documento_origen',
        'is_helper_assignment',
        'busqueda_avanzada_solo_sin_asignar',
        'busqueda_avanzada',
        'busqueda_avanzada_fecha_desde',
        'busqueda_avanzada_fecha_hasta'
    )
    def get_documentos_compra_init(self):
        self.documentos_compra_sin_filtrar = [(6,0, self.get_documentos_compra_init_gen())]

    @api.multi
    def get_documentos_compra_init_gen(self):
        self.ensure_one()
        company_id = self.env.user.company_id
        if not bool(company_id):
            company_id = self.env['res.users'].sudo().browse(self.env.uid).company_id
        domain = [
            ('source_service', '=', self.documento_origen.name),
            ('invoice_status', '!=', 'invoiced'),
            ('state', 'not in', ('cancel', 'done')),
            ('internal_helper_purchase', '=', self.is_helper_assignment),
            ('company_id','=',company_id.id),
            *self.advance_search_domains
        ]
        result = self.env['purchase.order'].sudo().search(domain)
        return result.ids

    @api.multi
    def set_driver_btn(self):
        conductor_defecto_id = int(self.sudo().env['ir.config_parameter'].sudo().get_param('default_driver_id'))
        ayudante_defecto_id = int(self.sudo().env['ir.config_parameter'].sudo().get_param('default_helper_id'))
        for this in self:
            documentos_compra = self.env['purchase.order'].sudo().browse(this.get_documentos_compra_init_gen()).filtered(lambda POrder: this.filter_po(POrder))
            if documentos_compra:
                this.documentos_compra_sin_filtrar = [(5, )]
                documentos_compra.write({
                    'partner_id': this.conductor.id,
                    'driver_state': "set" if this.conductor.id not in (conductor_defecto_id, ayudante_defecto_id) else "not_set"
                })
                documentos_compra.filtered(lambda doc: doc.state == 'draft').button_confirm()
                documentos_compra.mapped('picking_ids').write({
                    'partner_id': this.conductor.id
                })
            else:
                raise UserWarning("No se hay ningun documento que asignar segun sus criterios de busqueda.ss")
