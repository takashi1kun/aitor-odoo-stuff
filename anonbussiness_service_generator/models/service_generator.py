# -*- coding: utf-8 -*-
# (c) 2019 2020 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta
import ast
from odoo import models, fields, api, exceptions, _
from datetime import datetime, timedelta, date as datedate
from odoo.exceptions import UserError

def indexmap(fn, iterable):
    return map(fn, iterable, range(iterable.__len__()))

class SaleOrderServiceGenerator(models.Model):
    _name = 'sale.order.service.generator'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Generador Raiz de Servicios"

    name = fields.Char(default="Nuevo",
                       copy=False, index=True, track_visibility='always')
    note = fields.Html("Nota", sanitize=False, sanitize_attributes=False, sanitize_tags=False, sanitize_style=False, strip_style=False, strip_classes=False,copy=False)
    company_id = fields.Many2one(
        'res.company',
        string='Comapañia',
        readonly=True,
        required=True,
        copy=False,
        index=True,
        default=lambda self: self.env.user.company_id.id)
    user_id = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        required=True,
        copy=False,
        string='Autor',
        index=True,
        default=lambda self: self.env.user,
    )
    creation_date = fields.Date(
        string='Fecha de Creacion',
        readonly=True,
        copy=False,
        index=True,
        default=datetime.today()
    )
    last_update_date = fields.Date(
        string='Ultima modificacion',
        index=True,
        copy=False,
        default=datetime.today()
    )
    active = fields.Boolean('Activo', default=True)
    generation_date = fields.Date(
        copy=False, string="Fecha de Generacion")
    confirmation_date = fields.Date(
        copy=False, string="Fecha de Confirmacion")
    cancelation_date = fields.Date(string="Fecha de Eliminacion",
                                   copy=False)
    state = fields.Selection([('draft', 'Borrador'), ('generado', 'Generado'), ('confirmado', 'Confirmado'), ('completado', 'Completado'),
                              ('cancelado', 'Cancelado')],
                             string="Estado",
                             copy=False, track_visibility='onchange', default="draft")
    service = fields.Selection([('fijo', 'FIJO'), ('planificado', 'PLANIFICADO'), ('ya', 'YA')],
                               string='Tipo de Servicio', default='fijo', track_visibility='always')
    operation_ids = fields.One2many('sale.operations', 'generator_id', string="Operaciones", copy=False)
    fixed_months = fields.Selection([("6", "6 meses"), ("12", "12 meses")], string="Duracion")
    fixed_starting = fields.Date(string="Fecha de inicio")
    planed_finish = fields.Date(string="Fecha de fin")
    fixed_lunes = fields.Boolean(string='Lunes')
    fixed_martes = fields.Boolean(string='Martes')
    fixed_miercoles = fields.Boolean(string='Miercoles')
    fixed_jueves = fields.Boolean(string='Jueves')
    fixed_viernes = fields.Boolean(string='Viernes')
    fixed_sabado = fields.Boolean(string='Sabado')
    fixed_domingo = fields.Boolean(string='Domingo')
    fixed_todos = fields.Boolean(string='Todos')

    completition = fields.Integer(string="% Completado", default=0)

    puede_haber_peajes = fields.Boolean(string='Habilitar Opcion de Peajes', default=True)

    prev_service = fields.Many2one("sale.order.service.generator", string="Servicio Anterior",
                                   copy=False)
    next_service = fields.Many2one("sale.order.service.generator", string="Servicio Siguiente",
                                   copy=False)

    half_done = fields.Boolean("Medio Hecho", default=False,
                               copy=False)
    tipo_producto = fields.Selection([('hr', 'Horas'), ('km', 'Kilometros'), ('jornada', 'Jornada')],
                                     string='tipo_producto')
    linked_sale_orders = fields.One2many(comodel_name='sale.order',
                                         copy=False, inverse_name='source_service',
                                         string='Ordenes de venta generadas')
    linked_purchase_orders = fields.One2many(comodel_name='purchase.order',
                                             copy=False, inverse_name='source_service',
                                             string='Ordenes de compra generadas')
    linked_stock_pickings = fields.One2many(comodel_name='stock.picking',
                                            copy=False, inverse_name='source_service',
                                            string='Albaranes generadas')

    linked_sale_orders_count = fields.Integer("Ventas Generadas", compute="_compute_linked_sale_orders_count",
                                              readonly=True)
    linked_purchase_orders_count = fields.Integer("Compras Generadas", compute="_compute_linked_purchase_orders_count",
                                                  readonly=True)
    linked_stock_pickings_count = fields.Integer("Albaranes Generados", compute="_compute_linked_stock_pickings_count",
                                                 readonly=True)

    producto = fields.Many2one( copy=False,comodel_name='product.product', string="Producto", track_visibility='always')
    horas = fields.Float( copy=False,string="Horas Contratadas")
    cliente = fields.Many2one(comodel_name="res.partner", string="Cliente", track_visibility='always')
    dias_calculados = fields.Char(string='Dias',
                                  copy=True)
    could_be_renewed = fields.Boolean(string="Podrian renovarse", default=False,
                                      copy=False)
    days_till_renovation = fields.Integer(string="Dias hasta la renovacion", copy=False, default=-1)
    has_internal_helper = fields.Boolean(string="Tiene Ayudante Interno?", copy=False, default=False)
    week_letters_arr = [
        "L ",
        "M ",
        "X ",
        "J ",
        "V ",
        "S ",
        "D "
    ]
    line_ids = fields.One2many('sale.order.service.generator.line', 'generator_id', "Lineas", copy=False)

    start_hour = fields.Float("Hora de comienzo", default=0.0)
    finish_hour = fields.Float("Hora de fin", default=0.0)
    free_night_hours = fields.Boolean("Horas Nocturnas Gratuitas", default=False)
    marked_for_generation = fields.Boolean("Marcado para generar", default=False)
    marked_for_double_generation = fields.Boolean("Marcado para generar", default=False)
    locked_for_generation = fields.Boolean("Generando", default=False)
    is_favorite = fields.Boolean(default=False, string='Mostrar en servicios favoritos',
        index=True, track_visibility='onchange',
                                 help="Controla si este servicio se mostrara en servicios favoritos")
    priority = fields.Selection(
        [('0','No Favorito'),('1','Favorito')], string='Favorito',
        compute='_compute_priority', inverse='_set_priority',
        # default='1', required=True,  # TDE: required, depending on moves ? strange
        help="Si es Favorito")

    tipo_tiempo_espera = fields.Selection(
        [('no', 'Sin Minutos de Espera'), ('moto', 'Moto'), ('coche', 'Coche')], default='no', required=True, string="Minutos de Espera"
    )
    disable_festive_saturday = fields.Boolean(string='Festividad Gratuita en Sabados', default=False)
    disable_festive_sunday = fields.Boolean(string='Festividad Gratuita en Domingos', default=False)
    disable_festive_calendar = fields.Boolean(string='Festividad Gratuita en Festividades del Calendario', default=False)

    @api.multi
    def recompute_completition(self):
        for this in self:
            if this.state == "confirmado":
                full = len(this.linked_purchase_orders)
                done = len(this.linked_stock_pickings.filtered(lambda x: x.state in ("cancel", "done")))
                if full>0 and full == done:
                    this.completition = 100
                    this.state = "completado"
                else:
                    completition = round((done * 100) / (full or 99999999999))
                    this.completition = completition if completition < 100 else 99
            elif this.state == "completado":
                this.completition = 100
            else:
                this.completition = 0

    @api.multi
    @api.depends("is_favorite")
    def _compute_priority(self):
        for this in self:
            this.priority = '1' if this.is_favorite else '0'

    @api.multi
    def _set_priority(self):
        for this in self:
            this.is_favorite = bool(this.priority == '1')

    @api.multi
    def mark_for_generation_double_later(self):
        self.write({
            "marked_for_double_generation": True,
            "marked_for_generation": False
        })

    @api.multi
    def mark_for_generation_later(self):
        self.write({
            "marked_for_generation": True,
            "marked_for_double_generation": False
        })

    @api.multi
    def delayed_generation(self):
        marked_for_generation = self.search([("marked_for_double_generation", "!=", True),("marked_for_generation", "=", True),("state", "=", "draft")])
        marked_for_confirmation = self.search([("marked_for_generation", "=", True),("state", "=", "generado")])
        marked_for_generation_confirmation = self.search([("marked_for_double_generation", "=", True),("state", "=", "draft")])
        every_one = self.browse(list(set([*marked_for_generation.ids,*marked_for_confirmation.ids,*marked_for_generation_confirmation.ids]))).exists()
        every_one.write({
            "locked_for_generation": True
        })
        marked_for_generation.action_generate()
        marked_for_confirmation.action_confirm()
        marked_for_generation_confirmation.action_generate()
        marked_for_generation_confirmation.action_confirm()
        every_one.write({
            "locked_for_generation": False,
            "marked_for_generation": False,
            "marked_for_double_generation": False
        })


    @api.multi
    def renew(self):
        for this in self:
            if this.date_start and this.date_end and this.service != 'ya':
                start = this.date_start
                if this.service == 'planificado':
                    newstart = this.date_end + timedelta(days=1)
                    difference = relativedelta(start, newstart).days
                    newend = newstart + relativedelta(days=abs(difference))
                else:
                    newstart = this.date_end + timedelta(days=1)
                    newend = False

                newOne = self.create({
                    'service': this.service,
                    'producto': this.producto,
                    'horas': this.horas,
                    'cliente': this.cliente,
                    'state': 'draft',
                    'user_id': this.user_id,
                    'fixed_lunes': this.fixed_lunes,
                    "dias_calculados": this.dias_calculados,
                    'fixed_martes': this.fixed_martes,
                    'fixed_miercoles': this.fixed_miercoles,
                    'fixed_jueves': this.fixed_jueves,
                    'fixed_viernes': this.fixed_viernes,
                    'fixed_sabado': this.fixed_sabado,
                    'fixed_domingo': this.fixed_domingo,
                    'fixed_todos': this.fixed_todos,
                    'tipo_producto': this.tipo_producto,
                    'fixed_starting': newstart,
                    'fixed_months': this.fixed_months,
                    'planed_finish': this.planed_finish if this.service != "planificado" else newend,
                    'prev_service': this.id
                })
                new_lines = this.line_ids.generate_copy(newOne)
                operationids = self.env["sale.operations"]
                for operation in this.operation_ids:
                    operationids |= this.operation_ids.create({
                        'ref': operation.ref,
                        'action': operation.action,
                        'dir': operation.dir,
                        'fecha': operation.fecha,
                        'hora': operation.hora,
                        'n_bultos': operation.n_bultos,
                        'persona_contacto': operation.persona_contacto,
                        'telf': operation.telf,
                        'generator_id': newOne.id
                    })
                this.next_service = newOne.id
        self._calc_could_be_renewed()

    @api.model
    def renew_cron(self):
        self.sudo().search([
            ("state", "in", ("confirmado", "completado")),
            ("service", "!=", "ya")
        ])._calc_could_be_renewed()

    # @api.multi
    # @api.depends('service', 'planed_finish', 'fixed_months', 'fixed_starting', 'state')
    # def _calc_could_be_renewed_auto(self):
    #     self._calc_could_be_renewed()

    @api.multi
    def recalculate_providers_price(self):
        product_ids = self.env["product.product"].search([("service_type_praxya", "in", ("ya", "fijo", "planificado"))])
        product_ids.recalculate_price_for_provider()

    @api.multi
    def create_provider_lines(self):
        product_ids = self.env["product.template"].search([("service_type_praxya", "in", ("ya", "fijo", "planificado"))])
        product_ids.regenerate_providers()

    @api.multi
    def autofill_ya_by_category(self):
        no_product_ya_hr = ("product_ya_id", '=', False)
        no_product_ya_km = ("product_ya_km_id", '=', False)
        servicio_fijo_o_planificado = ("service_type_praxya", 'in', ("fijo", "planificado"))
        servicios_transporte = ("service_type_praxya", "in", ("ya", "fijo", "planificado"))
        servicio_es_ya = ("service_type_praxya", '=', "ya")
        es_uom_km = ("uom_id", '=', self.km_uom.id)
        es_uom_hr = ("uom_id", '=', self.hr_uom.id)
        es_uom_jornada = ("uom_id", '=', self.jornada_uom.id)
        OR = "|"
        AND = "&"
        product_ids = self.env["product.template"].search([
            AND,
                servicios_transporte,
                OR,
                    AND,
                        servicio_fijo_o_planificado,
                        OR,
                            no_product_ya_hr,
                            no_product_ya_km,
                    AND,
                        servicio_es_ya,
                        OR,
                            OR,
                                AND,
                                    es_uom_km,
                                    no_product_ya_hr,
                                AND,
                                    es_uom_hr,
                                    no_product_ya_km,
                            OR,
                                AND,
                                    es_uom_jornada,
                                    no_product_ya_km,
                                AND,
                                    es_uom_jornada,
                                    no_product_ya_hr
        ])
        product_ids.autofill_ya_by_category()


    @api.multi
    def param(self, param, is_float=False):
        val = self.sudo().env['ir.config_parameter'].sudo().get_param(param)
        if is_float:
            return float(val)
        else:
            return int(val)

    @property
    @api.multi
    def hr_uom(self):
        return self.env["product.product"].browse(self.param('hr_uom_id'))

    @property
    @api.multi
    def km_uom(self):
        return self.env["product.product"].browse(self.param('km_uom_id'))


    @property
    @api.multi
    def jornada_uom(self):
        return self.env["product.product"].browse(self.param('jornada_uom_id'))

    @api.multi
    def _calc_could_be_renewed(self):
        for this in self:
            if this.service == "ya" or this.state in ("draft", "generado", "cancelado"):
                this.could_be_renewed = False
                this.days_till_renovation = -1
            else:
                end = this.date_end
                today = datedate.today()
                day_difference = (end - today).days
                if today > end:
                    this.could_be_renewed = True
                    this.days_till_renovation = 0
                elif this.service == "ya":
                    delta = relativedelta(end, today)
                    delta_in_months = delta.months + delta.years * 12
                    this.could_be_renewed = delta_in_months <= 1
                    this.days_till_renovation = day_difference
                else:  # this.service == 'planificado'
                    this.could_be_renewed = day_difference <= 15
                    this.days_till_renovation = day_difference

    @api.multi
    @api.depends('linked_sale_orders')
    def _compute_linked_sale_orders_count(self):
        for this in self:
            this.linked_sale_orders_count = len(this.linked_sale_orders.ids)

    @api.multi
    @api.depends('linked_purchase_orders')
    def _compute_linked_purchase_orders_count(self):
        for this in self:
            this.linked_purchase_orders_count = len(this.linked_purchase_orders.ids)

    @api.multi
    @api.depends('linked_stock_pickings')
    def _compute_linked_stock_pickings_count(self):
        for this in self:
            this.linked_stock_pickings_count = len(this.linked_stock_pickings.ids)

    @api.multi
    def button_sales(self):
        sales = self.mapped('linked_sale_orders')
        if sales:
            view_tree_id = self.env.ref('sale.view_order_tree').id
            view_form_id = self.env.ref('sale.view_order_form').id
            names = self.mapped("name")
            name_string = self.name if len(names) == 1 else ', '.join(names)
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', sales.ids)],
                'views': [(view_tree_id, 'tree'), (view_form_id, 'form')],
                'view_mode': 'tree, form',
                'name': 'Ordenes de Venta de %s' % name_string,
                'res_model': 'sale.order',
                'target': 'current'
            }
            return action

    @api.multi
    def button_purchases(self):
        self._calc_could_be_renewed()
        purchases = self.mapped('linked_purchase_orders')
        if purchases:
            view_tree_id = self.env.ref('purchase.purchase_order_tree').id
            view_form_id = self.env.ref('purchase.purchase_order_form').id
            names = self.mapped("name")
            name_string = self.name if len(names) == 1 else ', '.join(names)
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', purchases.ids)],
                'views': [(view_tree_id, 'tree'), (view_form_id, 'form')],
                'view_mode': 'tree, form',
                'name': 'Ordenes de Compra de %s' % name_string,
                'res_model': 'purchase.order',
                'target': 'current'
            }
            return action

    @api.multi
    def button_pickings(self):
        self._calc_could_be_renewed()
        pickings = self.mapped('linked_stock_pickings')
        if pickings:
            view_tree_id = self.env.ref('stock.vpicktree').id
            view_form_id = self.env.ref('stock.view_picking_form').id
            names = self.mapped("name")
            name_string = self.name if len(names) == 1 else ', '.join(names)
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', pickings.ids)],
                'views': [(view_tree_id, 'tree'), (view_form_id, 'form')],
                'view_mode': 'tree, form',
                'name': 'Albaranes de %s' % name_string,
                'res_model': 'stock.picking',
                'target': 'current'
            }
            return action

    @api.multi
    def action_driver_wizard(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('anonbussiness_service_generator', 'wizard_assignment_driver_action')
        context = ast.literal_eval(res.get("context", "{}"))
        res.update({
            'name': 'Asignar Conductores de %s' % self.name,
            'context': {**context,'default_documento_origen': self.id, 'default_readonly_origen': True}
        })
        return res

    @api.multi
    def action_helper_wizard(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('anonbussiness_service_generator', 'wizard_assignment_helper_action')
        context = ast.literal_eval(res.get("context", "{}"))
        res.update({
            'name': 'Asignar Ayudantes de %s' % self.name,
            'context': {**context,'default_documento_origen': self.id, 'default_readonly_origen': True}
        })
        return res

    @api.multi
    def transform_everything(self):
        self._calc_could_be_renewed()
        arr = self.env['product.template'].search([])
        default_km_hora_id = self.param('kilometros_extra_producto_defecto_id')
        default_km_hora = self.env['product.product'].browse([default_km_hora_id]).exists()
        all_purchases = self.env["purchase.order"].sudo().search([])
        conductor_defecto_id = self.param('default_driver_id')
        for purchase in all_purchases:
            if purchase.SO_id:
                if purchase.partner_id.is_driver:
                    purchase.driver_state = "not_set" if purchase.partner_id.id == conductor_defecto_id else "set"
                else:
                    purchase.driver_state = "no_driver"
            else:
                if purchase.origin:
                    sale = self.env["sale.order"].search([("name", "=", purchase.origin)], limit=1)
                    if sale:
                        purchase.SO_id = sale.id
                        purchase.SO_ids = [(4, sale.id)]
                        if purchase.partner_id.is_driver:
                            purchase.driver_state = "not_set" if purchase.partner_id.id == conductor_defecto_id else "set"
                        else:
                            purchase.driver_state = "no_driver"
                    else:
                        purchase.driver_state = "no_driver"
                else:
                    purchase.driver_state = "no_driver"
        products_change = self.env["product.template"]
        for product in arr:
            str = product.name
            if str.find("YA ") != -1 or str.find("Ya ") != -1:
                product.service_type_praxya = "ya"
                product.type = "consu"
                product.route_ids = False
                product.route_ids = list(map(lambda x: (4, x), default_km_hora.route_ids.ids))
                products_change |= product
                if len(product.seller_ids) == 0:
                    default_km_hora.seller_ids[0].copy(
                        {"product_tmpl_id": product.id, "company_id": product.company_id.id})
            elif str.find("FIJO ") != -1 or str.find("Fijo ") != -1:
                product.service_type_praxya = "fijo"
                product.type = "consu"
                product.route_ids = False
                product.route_ids = list(map(lambda x: (4, x), default_km_hora.route_ids.ids))
                products_change |= product
                if len(product.seller_ids) == 0:
                    default_km_hora.seller_ids[0].copy(
                        {"product_tmpl_id": product.id, "company_id": product.company_id.id})
            elif str.find("PLANIFICADO ") != -1 or str.find("Planificado ") != -1:
                product.service_type_praxya = "planificado"
                product.type = "consu"
                product.route_ids = False
                products_change |= product
                product.route_ids = list(map(lambda x: (4, x), default_km_hora.route_ids.ids))
                if len(product.seller_ids) == 0:
                    default_km_hora.seller_ids[0].copy(
                        {"product_tmpl_id": product.id, "company_id": product.company_id.id})
            else:
                product.service_type_praxya = "otro"
        sellers = products_change.mapped("seller_ids")
        for seller in sellers:
            seller.delay = 0

    @api.onchange('producto')
    def change_product_type(self):
        kmUom = self.param('km_uom_id')
        hrUom = self.param('hr_uom_id')
        jornadaUom = self.param('jornada_uom_id')
        productUom = self.producto.uom_id.id
        if productUom == kmUom:
            self.tipo_producto = "km"
            self.horas = 0.0
        elif productUom == hrUom:
            self.tipo_producto = "hr"
            self.horas = 0.0
        elif productUom == jornadaUom:
            self.tipo_producto = "jornada"
            self.horas = self.param('kilometros_por_jornada', is_float=True) / self.param('kilometros_por_hora', is_float=True)
        elif self.producto.id == False:
            self.tipo_producto = False
        else:
            self.producto = False
            self.tipo_producto = False
            raise exceptions.ValidationError(
                'Error P-1: Tipo de producto invalido, por favor seleccione un producto de tipo jornada, horas o km, o bien configure corectamente estos en configuracion')

    @api.onchange('fixed_lunes', 'fixed_martes', 'fixed_miercoles', 'fixed_jueves', 'fixed_viernes', 'fixed_sabado',
                  'fixed_domingo')
    def unselect_all(self):

        self.fixed_todos = (
                self.fixed_lunes and self.fixed_martes and self.fixed_jueves and self.fixed_viernes and
                self.fixed_miercoles and self.fixed_sabado and self.fixed_domingo)
        week_arr = [
            self.fixed_lunes,
            self.fixed_martes,
            self.fixed_miercoles,
            self.fixed_jueves,
            self.fixed_viernes,
            self.fixed_sabado,
            self.fixed_domingo
        ]
        self.dias_calculados = ", ".join([x["a"] for x in list(map(lambda x, y: {"a": x, "b": y},
                                                                   self.week_letters_arr, week_arr)) if x["b"]])

    @property
    @api.multi
    def datetime_start(self):
        self.ensure_one()
        return datetime.strptime(
            self.fixed_starting, "%Y-%m-%d"
        ) if isinstance(self.fixed_starting, str) else False

    @property
    @api.multi
    def datetime_end(self):
        self.ensure_one()
        if self.service == "fijo":
            return datetime.strptime(
                self.fixed_starting, "%Y-%m-%d"
            ) + relativedelta(
                months=int(self.fixed_months)
            ) if isinstance(self.fixed_starting, str) and self.fixed_months else False
        else:
            return datetime.strptime(
                self.planed_finish, "%Y-%m-%d"
            ) if isinstance(self.planed_finish, str) else False

    @property
    @api.multi
    def date_start(self):
        self.ensure_one()
        return self.datetime_start.date() if self.datetime_start else False

    @property
    @api.multi
    def date_end(self):
        self.ensure_one()
        return self.datetime_end.date() if self.datetime_end else False

    @api.multi
    @api.onchange('service')
    def change_months(self):
        for this in self:
            if this.service == 'fijo':
                this.fixed_months = "6"
            else:
                this.fixed_months = ""
            if len(this.line_ids) > 0:
                this.line_ids.filtered(
                    lambda line: line.line_type in ('primary', 'secondary') and line.product_id).change_service(
                    this.service)
                this.line_ids._onchange_product_id()
                this.line_ids.recompute_possible_products()

    @api.multi
    @api.onchange('fixed_todos')
    def select_all(self):
        if self.fixed_todos:
            self.fixed_lunes = True
            self.fixed_martes = True
            self.fixed_jueves = True
            self.fixed_viernes = True
            self.fixed_miercoles = True
            self.fixed_sabado = True
            self.fixed_domingo = True
        elif (not self.fixed_todos and self.fixed_lunes and self.fixed_martes and self.fixed_jueves
              and self.fixed_viernes and self.fixed_miercoles and self.fixed_sabado and self.fixed_domingo):
            self.fixed_lunes = False
            self.fixed_martes = False
            self.fixed_jueves = False
            self.fixed_viernes = False
            self.fixed_miercoles = False
            self.fixed_sabado = False
            self.fixed_domingo = False
        week_arr = [
            self.fixed_lunes,
            self.fixed_martes,
            self.fixed_miercoles,
            self.fixed_jueves,
            self.fixed_viernes,
            self.fixed_sabado,
            self.fixed_domingo
        ]
        self.dias_calculados = ", ".join([x["a"] for x in list(map(lambda x, y: {"a": x, "b": y},
                                                                   self.week_letters_arr, week_arr)) if x["b"]])

    # Esta funciones son para comprobar que si es una planificada, que no exceda los 6 meses
    def am_i_right(self, tipo, fecha_inicio, fecha_fin):
        return (datetime.strptime(fecha_fin or "2019-01-01", "%Y-%m-%d") -
                datetime.strptime(fecha_inicio or "2019-01-01", "%Y-%m-%d")).days < 182 or tipo != "planificado"

    @api.multi
    def write(self, vals):
        vals["last_update_date"] = datetime.now()
        for this in self:
            if not (this.am_i_right(vals.get("service") or this.service, vals.get("fixed_starting") or this.fixed_starting,
                                vals.get("planed_finish") or this.planed_finish)):
                raise exceptions.ValidationError("Servicios de tipo planificado no pueden superar los 6 meses")
        return super(SaleOrderServiceGenerator, self).write(vals)


    @api.model
    def create(self, vals):
        if (self.am_i_right(vals.get("service"), vals.get("fixed_starting"), vals.get("planed_finish"))):
            vals['name'] = self.env['ir.sequence'].next_by_code('SVROOT') or _('New')
            res = super(SaleOrderServiceGenerator, self).create(vals)
            return res
        else:
            raise exceptions.ValidationError("Servicios de tipo planificado no pueden superar los 6 meses")

    def plus_time(self, date, extra):
        # A esta funcion le pasas un datetime object con la fecha de inicio y un int con la cantidad de meses que quieres
        # sumar y te calcula la fecha de fin
        return date + relativedelta(months=int(extra))
        # a = date
        # y = a.year

        # extra += a.month
        # if extra > 12:
        #    while extra > 12:
        #        y += 1
        #        extra -= 12
        # return datetime.strptime(str(y) + "-" + str(int(extra)) + "-" + str(a.day), "%Y-%m-%d")

    @api.multi
    def action_generate(self):
        for this in self:
            if this.marked_for_generation:
                this.marked_for_generation = False
                this.user_for_generation = False
            default_driver_id = self.param('default_driver_id')
            if default_driver_id == "0":
                raise exceptions.ValidationError("El conductor por defecto no esta configurado")
            if this.start_hour < 0.0 or this.start_hour > 23.99 or this.finish_hour < 0.0 or this.finish_hour > 23.99:
                raise exceptions.ValidationError(
                    "La hora de inicio o la de fin son superior a 23:59 o inferiores a 0:00, esto no esta permitido")
            #default_driver = self.env['res.partner'].browse([default_driver_id]).exists()
            if len(this.line_ids) == 0:
                raise exceptions.ValidationError(
                    "No hay lineas en este servicio, esto no es permitido, tiene que tener al menos una linea")
            elif not this.line_ids.is_product_defined:
                raise exceptions.ValidationError("Hay alguna linea de servicio sin producto, esto no esta permitido")
            else:
                type_lines = this.line_ids.mapped("line_type")
                if "primary" not in type_lines:
                    raise exceptions.ValidationError("No hay lineas primarias en este servicio, esto no esta permitido")
                elif type_lines.count("primary") > 1:
                    raise exceptions.ValidationError(
                        "Hay mas de una linea primaria en este servicio, esto no esta permitido")
                line_errors = this.line_ids.generation_test()
                if line_errors.has_errors:
                    error = "Se han encontrado los siguientes errores dentro de las lineas:\n\n"
                    for err in line_errors.errors:
                        error = "%s    > %s\n\n" % (error, err)
                    raise exceptions.ValidationError(error)
            # En esta funcion vamos a crear una purchase order por cada dia de entre el rango de fechas segun los dias de
            # la semana que han introducido
            week_arr = [
                this.fixed_lunes,
                this.fixed_martes,
                this.fixed_miercoles,
                this.fixed_jueves,
                this.fixed_viernes,
                this.fixed_sabado,
                this.fixed_domingo
            ]  # esta es una array de booleanos para procesar mas adelante si se ejecutara codigo en ese dia de la semana

            week_name_arr = [
                "lunes",
                "martes",
                "miercoles",
                "jueves",
                "viernes",
                "sabado",
                "domingo"
            ]  # esta array es simplemente para dar nombre a cada dia de la semana porque datetime devuelve un numero del 0-6
            date_start = this.datetime_start
            # aqui compruebo de que tipo es el servicio, si planificado fijo o ya
            if this.service == "planificado":
                # si es planificado simplemente pongo en la variable el valor del campo
                date_end = this.datetime_end
                name = self.env['ir.sequence'].sudo().next_by_code('SOPL') or _('New')
                POname = self.env['ir.sequence'].sudo().next_by_code('POPL') or _('New')
            elif this.service == "fijo":
                # si es fijo, paso la fecha inicio y los meses a una funcion para calcular la fecha fin
                date_end = this.datetime_end
                name = self.env['ir.sequence'].sudo().next_by_code('SOFJ') or _('New')
                POname = self.env['ir.sequence'].sudo().next_by_code('POFJ') or _('New')
            else:
                # si es YA, finalizo la funcion y continuo el flujo normal
                date_end = date_start if not this.datetime_end else this.datetime_end
                name = self.env['ir.sequence'].sudo().next_by_code('sale.order') or _('New')
                POname = self.env['ir.sequence'].sudo().next_by_code('purchase.order') or _('New')

            # Esto crea una array de fechas desde la fecha de inicio a la fecha de fin
            # date_range = [date_start + timedelta(days=x) for x in range(0, (date_end - date_start).days+1)]
            date_range = list(filter(lambda day: week_arr[day.weekday()],
                                     map(lambda extra_days: date_start + timedelta(days=extra_days),
                                         range(0, (date_end - date_start).days + 1))))
            if this.service == "ya":
                if this.date_end:
                    if len(date_range) == 0:
                        raise exceptions.ValidationError(
                            "Has creado un servicio YA de varios dias, pero no has activado ningun dia de la semana en este rango en este servicio YA, esto no esta permitido"
                        )
                    elif len(date_range) > 15:
                        raise exceptions.ValidationError(
                            "Has creado un servicio YA de varios dias, pero teniendo en cuenta los dias de la semana marcados y el rango de fechas que has especificado, hay mas de 15 dias, esto no esta permitido en servicios YA, porfavor use un planificado o fijo"
                        )
                else:
                    if not week_arr[this.datetime_start.weekday()]:
                        raise exceptions.ValidationError(
                            "Has creado un servicio YA de un solo dia, pero no has activado el dia de la semana que sucede este servicio YA, esto no esta permitido")
            elif this.service == "planificado":
                if len(date_range) == 0:
                    raise exceptions.ValidationError(
                        "Has creado un servicio planificado, pero teniendo en cuenta los dias de la semana marcados y el rango de fechas que has especificado, no se generaria ningun servicio, esto no esta permitido"
                    )
                elif relativedelta(date_end, date_start).months >= 6:
                    raise exceptions.ValidationError(
                        "Has creado un servicio planificado, pero teniendo en cuenta el rango de fechas que has especificado pasan mas de 6 meses, esto no esta permitido en servicios planificados, porfavor use un servicio FIJO para casosde 6 meses o 12 meses"
                    )
            else:
                if week_arr.count(True) == 0:
                    raise exceptions.ValidationError(
                        "Has creado un servicio FIJO, pero no no has marcado ningun dia de la semana, esto no esta permitido"
                    )

            # creo un indice y lo pongo a 1 para la numeracion en el nombre
            #hr_uom_id = this.producto.uom_id.id
            # calculo segun los dias de la semana y la array si el formato del indice es 000 o 00 o 0
            #number_length = len(str(int(len(date_range) / 7 * sum(week_arr))))
            this.generation_date = datetime.now()
            lines = list(map(lambda ln: (0, 0, {
                'name': ln.product_id.name,
                'line_type': ln.line_type,
                "customer_lead": ln.product_id.sale_delay,
                'product_id': ln.product_id.id,
                "create_date": this.generation_date,
                "company_id": this.company_id.id,
                "create_uid": this.user_id.id,
                'price_unit': ln.unit_price,
                'product_uom': ln.uom_id.id,
                'product_uom_qty': ln.product_qty or ln.product_qty_hours,
            }), this.line_ids))
            accepted_days = list(filter(lambda x: week_arr[x.weekday()],date_range))
            default_order = {
                "origin": this.name,
                "currency_id": self.sudo().env.ref('base.main_company').sudo().currency_id.id,
                "partner_invoice_id": this.cliente.id,
                "partner_shipping_id": this.cliente.id,
                "partner_id": this.cliente.id,
                "create_uid": this.user_id.id,
                "create_date": this.generation_date,
                "company_id": this.company_id.id,
                "operation_ids": [(6, 0, this.operation_ids.ids)],
                "service_driver_praxya": this.service,
                "order_line": lines
            }
            sale_orders = indexmap(lambda x, i: (0,0,{
                **default_order,
                "name": "%s-%03i-%s" % (name, i+1, week_name_arr[x.weekday()]),
                "date_order": x.strftime("%Y-%m-%d"),
                "date_planned": x.strftime("%Y-%m-%d"),
                "generated_id": i+1,
                "week_day": week_name_arr[x.weekday()],
                "PO_name": "%s-%03i-%s" % (POname, i+1, week_name_arr[x.weekday()])
            }), accepted_days)
            this.linked_sale_orders = list(sale_orders)
            sale_order_ids = this.linked_sale_orders #self.env["sale.order"].create(sale_orders)
            so_line_ids = sale_order_ids.mapped("order_line")
            for line in so_line_ids:
                line._onchange_discount()

            this.state = "generado"
        self._calc_could_be_renewed()
        # return {
        #    'type': 'ir.actions.client',
        #    'tag': 'reload',
        # }

    @api.multi
    def cancel_sales_purchases(self):
        filterLambda = lambda order: order.state not in ("done", "cancel")
        self.mapped("linked_purchase_orders").sudo().filtered(filterLambda).sudo().button_cancel()
        self.mapped("linked_sale_orders").sudo().filtered(filterLambda).sudo().action_cancel()

    @api.multi
    def action_cancel(self):
        self._calc_could_be_renewed()
        for this in self:
            if this.state == "completado":
                pass
            if this.state == "confirmado":
                this_sudo = this.sudo()
                this_sudo.active = False
                this_sudo.cancel_sales_purchases()
                this_sudo.state = "cancelado"
                this_sudo.half_done = True
            else:
                this.active = False
                this.cancelation_date = datetime.now()
                this.generation_date = False
                this.state = "cancelado"
                a = this.linked_sale_orders
                b = this.linked_purchase_orders
                c = this.linked_stock_pickings

                for x in c:
                    x.state = "cancel"
                    x.unlink()
                for x in b:
                    x.state = "cancel"
                    x.unlink()
                for x in a:
                    x.state = "cancel"
                    x.unlink()
        # return {
        #    'type': 'ir.actions.client',
        #    'tag': 'reload',
        # }

    @api.multi
    def action_delete(self):
        for this in self:
            for line in this.line_ids:
                line.unlink()
            for operation in this.operation_ids:
                operation.unlink()
            this.unlink()
        action = self.env.ref('anonbussiness_service_generator.action_sale_order_service_generator').read()[0]
        return action

    @api.multi
    def action_draft(self):
        for this in self:
            this.active = True
            this.state = 'draft'
            this.cancelation_date = False
        self._calc_could_be_renewed()
        # return {
        #    'type': 'ir.actions.client',
        #    'tag': 'reload',
        # }

    @api.multi
    def check_if_days_week_exists(self):
        self.ensure_one()
        week_arr = [
            self.fixed_lunes,
            self.fixed_martes,
            self.fixed_miercoles,
            self.fixed_jueves,
            self.fixed_viernes,
            self.fixed_sabado,
            self.fixed_domingo
        ]
        formatoFecha = "%Y-%m-%d"
        date_start = self.datetime_start
        if self.service == "planificado":
            date_end = self.datetime_end
        elif self.service == "fijo":
            date_end = self.datetime_end
        else:
            date_end = date_start
            week_arr = [
                True,
                True,
                True,
                True,
                True,
                True,
                True,
            ]
        days_happened = (date_end - date_start).days
        if days_happened <= 7:
            date_range = [date_start + timedelta(days=x) for x in range(0, days_happened + 1)]
            return any(map(lambda x: week_arr[x.weekday()], date_range))
        else:
            return any(week_arr)

    @api.multi
    def validation_confirm(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.product_qty <= 0:
                raise UserError("Solo si el tipo de producto es jornada se puede dejar horas o kilometros en blanco, "
                                "pero el tipo de prodcuto que ha introducido no es jornada y ha dejado las horas "
                                "o kilometros en blanco.")
        if not (self.fixed_lunes or self.fixed_martes or self.fixed_jueves or self.fixed_viernes or
                self.fixed_miercoles or self.fixed_sabado or self.fixed_domingo):
            raise UserError("No ha seleccionado ningun dia de la semana, tiene que seleccionar un dia como minimo")
        if not self.check_if_days_week_exists():
            raise UserError("Los dias de la semana que ha seleccionado no se encuentran entre las fechas indicadas")

    @api.multi
    def action_confirm(self):
        for this in self:
            if this.marked_for_generation:
                this.marked_for_generation = False
                this.user_for_generation = False
            this.validation_confirm()
            this.confirmation_date = datetime.now()
            this.state = 'confirmado'
            a = this.linked_sale_orders
            for x in a:
                x.action_confirm()
            if len(this.line_ids.filtered(lambda x: x.line_type == "helper" and x.product_id.helper_type == "internal_helper")):
                this.has_internal_helper = True
        self._calc_could_be_renewed()
        # return {
        #    'type': 'ir.actions.client',
        #    'tag': 'reload',
        # }

    @property
    @api.multi
    def primary_line_defined(self):
        primary = self.line_ids.filtered(lambda line: line.line_type == "primary")
        if not primary:
            return False
        else:
            if primary[0].product_id:
                return True
            else:
                return False

    line_button_available = fields.Selection(
        [('none', "Ninguno"), ('primary', "Primaria"), ('secondary/other', "Secundaria o otro")],
        default="primary", copy=False)

    @api.multi
    @api.depends("state")
    def update_line_buttons_available(self):
        for this in self:
            this.line_button_available = self.line_buttons_available()

    @api.multi
    def line_buttons_available(self):
        if self.state != "draft":
            return "none"
        elif self.primary_line_defined:
            return "secondary/other"
        else:
            return "primary"

    @api.multi
    def create_line(self, type):
        orders = {
            "primary": 1,
            "secondary": 2,
            "helper": 3,
            "other": 4
        }
        new_line_id = self.env['sale.order.service.generator.line'].create({
            "generator_id": self.id,
            "line_type": type,
            "order_number": orders[type]
        })
        new_line_id.recompute_possible_products()
        new_line_id._calculate_can_be_deleted()

    @api.multi
    def delete_line(self, line_ids):
        line_ids.unlink()

    @api.multi
    def action_create_main_line(self):
        self.ensure_one()
        if not self.primary_line_defined:
            self.create_line(type="primary")
            self.line_button_available = "secondary/other"

    @api.multi
    def action_create_secondary_line(self):
        self.ensure_one()
        if self.primary_line_defined:
            self.create_line(type="secondary")
            self.line_ids.recompute_possible_products()
            self.line_ids.block_primary()

    @api.multi
    def action_create_misc_line(self):
        self.ensure_one()
        if self.primary_line_defined:
            self.create_line(type="other")

    @api.multi
    def action_create_helper_line(self):
        self.ensure_one()
        if self.primary_line_defined:
            self.create_line(type="helper")


class RangeComparation(object):
    __slots__ = ["x_range", "y_range", "overlap", "x_overflow", "y_overflow", "overlap_start", "overlap_end"]

    def __init__(self, x1, x2, y1, y2):
        self.x_range = (x1, x2)
        self.y_range = (y1, y2)
        range1 = max(x1, y1)
        range2 = min(x2, y2)
        overlap = range2 - range1
        self.x_overflow = x2 - x1 - overlap
        self.y_overflow = y2 - y1 - overlap
        self.overlap_start = range1
        self.overlap_end = range2
        self.overlap = overlap

    @property
    def values(self):
        return (self.x_range[0], self.x_range[1], self.y_range[0], self.y_range[1], self.overlap, self.x_overflow, self.y_overflow, self.overlap_start, self.overlap_end)

    def __repr__(self):
        return "x_range: %i - %i\ny_range: %i - %i\noverlap: %i\nx_overflow: %i\ny_overflow: %i\noverlap_start: %i\noverlap_end: %i" % self.values

    def __str__(self):
        return "x_range: %i - %i\ny_range: %i - %i\noverlap: %i\nx_overflow: %i\ny_overflow: %i\noverlap_start: %i\noverlap_end: %i" % self.values

    def __bool__(self):
        return self.overlap != 0

    def __int__(self):
        return self.overlap

    def __len__(self):
        return self.overlap

    def __contains__(self, item):
        try:
            return self.overlap_start <= item <= self.overlap_end
        except TypeError:
            raise TypeError("can only check contains for integers")

    def __float__(self):
        return self.overlap / (self.x_range[1] - self.x_range[0]) if bool(self) else 0.0

    def __eq__(self, other):
        return int(self) == int(other)

    def __iter__(self):
        return iter(range(self.overlap_start, self.overlap_end))