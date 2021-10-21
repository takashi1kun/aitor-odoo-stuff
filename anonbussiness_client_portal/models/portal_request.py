# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


def dict_to_tuples(dictionary):
    return list(dictionary.items())


STATES = {
    'new': 'Nuevo',
    'draft': 'Borrador',
    'requested': 'Solicitado',
    'confirmed': 'Confirmado',
    'completed': 'Completado',
    'cancel': 'Cancelado'
}

TYPES = {
    'recogida': 'Recogida',
    'insercion_documento': 'Insercion de Documento',
    'peticion': 'Consulta',
    'peticion_digital': 'Peticion Digital',
    'devolucion': 'Devolucion',
    'digitalizacion': 'Digitalizacion',
    'baja': 'Baja',
    'destruccion': 'Destruccion'
}

METHOD = {
    'manual': 'Manual',
    'carga_masiva': 'Carga Masiva'
}

AND = "&"
OR = "|"


class PortalRequest(models.Model):
    _name = 'portal.request'
    _description = 'Petición de Servicio'
    _order = 'id desc'
    _date_name = 'creation_date'

    name = fields.Char(
        string="Nombre",
        compute="_compute_name"
    )
    code = fields.Char(
        string="Código",
        copy=False
    )
    state = fields.Selection(
        selection=dict_to_tuples(STATES),
        string="Estado",
        default='new',
        required=True,
        copy=False
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.uid,
        string="Usuario Cliente",
        required=True,
        copy=False,
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id.id,
        readonly=True
    )
    peticionario_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="user_id.partner_id"
    )
    company_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="user_id.partner_id.parent_id"
    )
    method = fields.Selection(
        selection=dict_to_tuples(METHOD),
        default="manual",
        required=True,
        string="Método de carga de datos"
    )
    service_id = fields.Many2one(
        comodel_name="product.product",
        domain=[
            ('type', '=', 'service'),
            ('tipo_servicio', 'not in ', ['none', 'custodia'])
        ],
        required=True,
        copy=False,
        readonly=True,
        states={
            'new': [('readonly', False)]
        }
    )

    allowed_product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        compute="_compute_allowed_product_tmpl_ids",
        compute_sudo=True
    )
    service_type = fields.Selection(
        selection=dict_to_tuples(TYPES),
        string="Tipo de Servicio",
        compute='_compute_service_type',
        store=True
    )
    qty_solicited = fields.Integer(
        string="Cantidad solicitada",
        copy=False
    )
    document_file = fields.Binary(
        string="Documento de subida masiva",
        copy=False
    )
    document_file_csv = fields.Binary(
        string="Documento de subida masiva",
        compute="_compute_document_file_csv"
    )
    #document_type_id = fields.Many2one(
    #    comodel_name="custody.case.level",
    #    copy=False
    #)
    #allowed_document_type_ids = fields.Many2many(
    #    comodel_name="custody.case.level",
    #    compute="_compute_allowed_document_type_ids"
    #)
    custody_document_ids = fields.Many2many(
        comodel_name="custody.document",
        relation="portal_request_to_documents_rel",
        column1="portal_request_id",
        column2="custody_document_id",
        string="Documentos",
        copy=False
    )
    creation_date = fields.Datetime(
        string="Fecha de creación",
        copy=False,
        readonly=True,
        states={
            'new': [('readonly', False)]
        }
    )
    request_date = fields.Datetime(
        string="Fecha de solicitud",
        copy=False,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        }
    )
    confirm_date = fields.Datetime(
        string="Fecha de confirmación",
        copy=False,
        readonly=True,
        states={
            'requested': [('readonly', False)]
        }
    )
    complete_date = fields.Datetime(
        string="Fecha de confirmación de la venta",
        copy=False,
        readonly=True,
        states={
            'confirmed': [('readonly', False)]
        }
    )
    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Venta",
        copy=False
    )

    note = fields.Text(
        string="Notas y comentarios"
    )

    @api.multi
    @api.depends('document_file')
    def _compute_document_file_csv(self):
        for this in self:
            this.document_file_csv = this.document_file

    @api.model
    def get_next_code(self):
        return self.env['ir.sequence'].sudo().next_by_code('portal.request')

    @api.model
    def create(self, vals):
        res = super(PortalRequest, self).create(vals)
        if res.state == "draft" and not res.code:
            res.code = self.get_next_code() or ''
        return res

    @api.model
    def get_base64_data(self, field_name="", record_id=0):
        if record_id != 0:
            record = self.browse([record_id]).exists()
            if record and len(record.fields_get([field_name])) == 1:
                data = record.read([field_name])
                binarydata = data[0].get(field_name, False)
                if binarydata:
                    return str(binarydata)[2:-1]
        return ""

    @api.multi
    @api.depends("user_id")
    def _compute_allowed_product_tmpl_ids(self):
        for this in self:
            if this.user_id:
                this.allowed_product_tmpl_ids = this.user_id.partner_id.parent_id.allowed_product_tmpl_ids_getter

    @api.constrains('qty_solicited', 'method', 'state', 'service_id')
    def _check_qty(self):
        for this in self:
            if this.method == "manual" and this.service_id and this.service_type in ['recogida', 'insercion_documento']:
                if this.qty_solicited < 0 and this.state in ["draft", "cancel"]:
                    raise ValidationError("La cantidad no puede ser negativa")
                elif this.qty_solicited < 1 and this.state in ["requested", "confirmed", "completed"]:
                    raise ValidationError("La cantidad tiene que ser 1 o superior")

    @api.constrains('document_file', 'method', 'state', 'service_id')
    def _check_file_masive(self):
        for this in self:
            if this.method == "carga_masiva" and this.service_id:
                if not this.document_file and this.state in ["requested", "confirmed", "completed"]:
                    raise ValidationError("Si se selecciona carga masiva, hay que subir un documento.")

    @api.constrains('custody_document_ids', 'method', 'state', 'service_id')
    def _check_documents(self):
        for this in self:
            if this.method == "manual" and this.service_id and this.service_type not in ['recogida', 'insercion_documento']:
                documents = this.custody_document_ids
                document_len = len(documents)
                if this.state in ["draft", "requested", "confirmed", "completed"]:
                    if document_len < 1 and this.state != "draft":
                        raise ValidationError("Tiene que haber al menos un elemento seleccionado.")
                    elif not all(map(lambda x: self.check_document(x), documents)):
                        raise ValidationError("No todos los elementos son del mismo tipo, no se pueden mezclar.")
                    elif this.service_id.almc_producto_id and document_len > 0 and documents[0].product_id.id != this.service_id.almc_producto_id.id:
                        # raise ValidationError("Los elementos que has seleccionado no coinciden con el servicio")
                        print("Los elementos que has seleccionado no coinciden con el servicio")

    @api.constrains('user_id', 'state', 'service_id')
    def _check_service_id(self):
        for this in self:
            if this.state != "new":
                if not this.service_id:
                    raise ValidationError("Sólo las solicitudes en estado nuevo pueden prescindir de servicio.")
                else:
                    allowed_service_ids = self.env['product.product'].sudo().search([
                        ('type', '=', 'service'),
                        ('allowed_partner_ids', '=', this.user_id.partner_id.parent_id.id),
                        ('tipo_servicio', 'not in', ['none', 'custodia'])
                    ]).ids
                    if this.service_id.id not in allowed_service_ids:
                        raise ValidationError("Este servicio no está dentro de los que puede contratar, si esto es un error, por favor contacte con nosotros.")

    @api.model
    def create_from_service(self, service):
        allowed_service_ids = self.env['product.product'].search([
            ('type', '=', 'service'),
            ('allowed_partner_ids', '=', self.env.user.partner_id.parent_id.id),
            ('tipo_servicio', 'not in', ['none', 'custodia'])
        ])
        if service.id not in allowed_service_ids.ids:
            raise ValidationError("Este servicio no está dentro de los que puede contratar, si esto es un error, por favor contacte con nosotros.")
        return {
            'default_user_id': self.env.user.id,
            'default_company_id': self.env.user.company_id.id,
            'default_service_id': service.id,
            'default_state': 'draft',
            'default_service_type': self.transform(service.tipo_servicio),
            'default_creation_date': fields.Datetime.now()
        }

    @api.model
    def create_from_documents(self, service, documents):
        new_request = self.create_from_service(service)
        new_request['context'] = {**new_request['context'],
                                  "default_custody_document_ids": documents.ids
                                  }
        return new_request

    @api.multi
    def new_to_draft(self):
        self.ensure_one()
        self.creation_date = fields.Datetime.now()
        if not self.code:
            self.code = self.get_next_code()
        self.state = "draft"

    @api.model
    def action_new_from_service(self, service_id):
        service = self.env['product.product'].search([("product_tmpl_id", "=", service_id)])
        new_request = self.create_from_service(service)
        action = self.env.ref('anonbussiness_client_portal.action_anonbussiness_client_portal_request').read()[0]
        if not action.get('context', False):
            action['context'] = dict(self.env.context)
        elif type(action.get('context')) == str:
            action['context'] = eval(action['context'])

        action['context']['form_view_initial_mode'] = 'edit'
        action['context']['view_no_maturity'] = False
        action['context'] = {**action['context'], **new_request}

        # action['res_id'] = new_request.id
        return action

    @api.multi
    def make_request(self):
        self.ensure_one()
        if self.state == "draft":
            self.request_date = fields.Datetime.now()
            self.state = "requested"

    @property
    @api.multi
    def input_type(self):
        self.ensure_one()
        if self.service_id:
            if self.method == "carga_masiva":
                return "csv"
            elif self.service_type in ['recogida', 'insercion_documento']:
                return "qty"
            else:
                return "doc"
        else:
            return "new"

    @api.multi
    def generate_sale(self):
        Sale = self.env['sale.order']
        for this in self:
            sale_id = Sale.create_sale_from_service(
                servicio=this.service_id,
                peticionario=this.peticionario_partner_id,
                cliente=this.company_partner_id,
                docs=this.custody_document_ids if this.input_type == "doc" else None,
                qty=this.qty_solicited if this.input_type == "qty" else None,
                csv=this.document_file if this.input_type == "csv" else None,
                origin=this.name
            )
            this.write({
                'sale_id': sale_id.id,
                'confirm_date': fields.Datetime.now(),
                'state': "confirmed",
            })

    @api.multi
    def cancel(self):
        self.ensure_one()
        # TODO: Implementar Checkeos
        if self.state in ["draft", "new"]:
            self.state = "cancel"
        elif self.state == "requested":
            self.sudo().write({
                'state': "draft",
                'request_date': False
            })

    @api.multi
    def go_to_sale(self):
        self.ensure_one()
        state = {
            'confirmed': 'sale.action_quotations',
            'completed': 'sale.action_orders'
        }
        original_action = self.env.ref(state[self.state]).read()[0]

        action = {
            **original_action,
            'context': eval(original_action.get('context', 'False')) or dict(self.env.context),
            'res_id': self.sale_id.id,
            'view_id': self.env.ref('sale.view_order_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(self.env.ref('sale.view_order_form').id, 'form')],
            'domain': ''
        }
        return action

    @api.multi
    def open_wizard(self):
        self.ensure_one()
        if not self.service_id:
            raise UserError('Primero hay que seleccionar el servicio')

        view_form_id = self.env.ref('custody_document_anonbussiness.custom_search_document_wizard_form').id
        context = dict(self._context or {})
        context = {
            **context,
            'default_portal_request_id': self.id,
            'default_oculta_info': True,
            'default_muestra_in_search': True,
            'default_partner_id': self.company_partner_id.id,
            "default_oculta_product": True,
            "default_tipo_busqueda": "diri"
        }
        if self.service_id.almc_producto_id:
            context = {
                **context,
                "default_product_ids": [self.service_id.almc_producto_id.id]
            }
        elif self.service_type == "peticion_digital":
            product_ids = self.env["product.product"].sudo().search([
                ("type", "=", "product"),
                ("custody_level_id", "!=", False),
                ("custody_level_id.level", "<", 3)
            ]).ids
            if len(product_ids):
                context = {
                    **context,
                    "default_product_ids": product_ids
                }

        action = {
            'type': 'ir.actions.act_window',
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': 'Seleccionar documentos',
            'target': 'new',
            'res_model': 'custom.search.document.wizard',
            'context': context
        }
        return action

    @api.model
    def transform(self, value):
        transformer = dict([
            ('baja', 'baja'),
            ('digitalizacion', 'digitalizacion'),
            ('pdigital', 'peticion_digital'),
            ('destruccion', 'destruccion'),
            ('devolucion', 'devolucion'),
            ('insercion', 'insercion_documento'),
            ('peticion', 'peticion'),
            ('recogida', 'recogida')])
        return transformer[value]

    @api.multi
    @api.depends('service_id')
    def _compute_service_type(self):
        for this in self:
            if this.service_id:
                this.service_type = self.transform(this.service_id.tipo_servicio)

    #@api.multi
    #@api.onchange("service_id")
    #def update_service_new(self):
    #    for this in self:
    #        if this.state == "new" and this.service_id:
    #            this.state = "draft"

    @api.multi
    @api.depends("state", "user_id", "service_id", "service_type", "code")
    def _compute_name(self):
        for this in self:
            if this.state == "new":
                this.name = "Nueva Solicitud de Servicio"
            elif this.code:
                this.name = this.code
            else:
                tipo = TYPES[this.service_type]
                if this.service_type != "insercion_documento" and this.service_id.almc_producto_id:
                    this.name = "Solicitud de %s de %s" % (tipo, this.service_id.almc_producto_id.name)
                else:
                    this.name = "Solicitud de %s" % tipo

    @api.multi
    def check_document(self, document):
        self.ensure_one()
        if self.service_type in ['peticion_digital', 'peticion']:
            product_ids = self.env["product.product"].sudo().search([
                ("type", "=", "product"),
                ("custody_level_id", "!=", False),
                ("custody_level_id.level", "<", 3)
            ]).ids
            return document.product_id.id in product_ids
        elif self.service_id.almc_producto_id:
            return document.product_id.id == self.service_id.almc_producto_id.id
        else:
            return True

    @api.multi
    def check_documents(self, documents):
        self.ensure_one()
        length = len(documents.mapped("product_id"))
        if length > 1:
            raise UserError("Sólo es posible añadir elementos del mismo tipo, ej. no puedes mezclar archivadores con documentos.")
        elif length == 1:
            checks = all(map(lambda x: self.check_document(x), documents))
            if not checks:
                raise UserError("En su selección hay elementos no permitidos en su servicio seleccionado")

    @api.multi
    def set_documents(self, document_ids):
        self.ensure_one()
        self.check_documents(self.env["custody.document"].sudo().browse(document_ids))
        res = list(map(lambda document_id: (4, document_id), document_ids))
        if len(res):
            self.custody_document_ids = res
        return res

