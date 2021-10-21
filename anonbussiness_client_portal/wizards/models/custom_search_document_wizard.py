# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class CustomSearchDocumentWizard(models.TransientModel):
    _inherit = "custom.search.document.wizard"

    portal_request_id = fields.Many2one("portal.request")
    filtered_domain = fields.Boolean()

    def get_tramo_documents(self, documents):
        service_product = self.portal_request_id.service_id.almc_producto_id
        if not bool(service_product):
            return documents

        doc_obj = self.env['custody.document']
        lote_obj = self.env['stock.production.lot']
        template_obj = self.env['product.template']
        servicio = template_obj.transform_tipo_servicio(self.portal_request_id.service_id.tipo_servicio)
        servicio = ('/' + servicio) if bool(servicio) else ""
        origin = self.portal_request_id.name + servicio

        tramos = documents.filtered(lambda x: x.product_id.id != service_product.id)
        res = documents.filtered(lambda x: x.id not in tramos.ids)
        for document in tramos:
            descripcion = (self.diri_descripcion or "") + " " + (self.diri_tramo or self.diri_anyo or self.diri_fecha or "")
            descripcion = descripcion.strip()

            doc_data = {
                'is_draft_tramo': True,
                'product_id': service_product.id,
                'parent_id': document.id,
                'owner_id': document.owner_id.id,
                'location_id': document.location_id.id,
                'tarea_last': origin,
                'custodia_state': document.custodia_state,
                'codigo_identificador': False,
                'etiqueta': False,
                'descripcion': descripcion.strip() or document.descripcion,
                'year_desde': self.diri_anyo or document.year_desde,
                'tramo_desde': self.diri_tramo or document.tramo_desde,
                'fecha_desde': self.diri_fecha or document.fecha_desde,
                'user_recepcion_id': document.user_recepcion_id.id,
                'user_inventario_id': self.env.uid,
                'user_ubicacion_id': document.user_ubicacion_id.id,
                'fecha_recepcion': document.fecha_recepcion,
                'fecha_inventario': fields.Date.today(),
                'fecha_ubicacion': document.fecha_ubicacion,
                'fecha_destruccion_prevista': document.fecha_destruccion_prevista,
                'tarea_recepcion': document.tarea_recepcion,
                'task_recepcion_id': document.task_recepcion_id.id,
                'tarea_inventario': origin,
                'task_inventario_id': False,
                'tarea_ubicacion': document.tarea_ubicacion,
                'task_ubicacion_id': document.task_ubicacion_id.id,
                'numero': document.numero,
                'texto': document.texto,
                'posicion': document.posicion,
                'referencia_cliente': document.referencia_cliente,
                'cliente_dpto': document.cliente_dpto,
                'document_coleccion_id': document.document_coleccion_id.id,
            }
            if bool(self.sel_adicional_1) and bool(self.diri_adicional_1):
                doc_data.update({self.sel_adicional_1: self.diri_adicional_1})
            if bool(self.sel_adicional_2) and bool(self.diri_adicional_2):
                doc_data.update({self.sel_adicional_2: self.diri_adicional_2})
            document = doc_obj.sudo().create(doc_data)
            res += document

        return res

    def add_documents(self):
        if not self.portal_request_id:
            return super(CustomSearchDocumentWizard, self).add_documents()
        else:
            documents = self.lines.filtered('seleccion').mapped('document_id')
            set_documents = self.get_tramo_documents(documents)
            self.portal_request_id.set_documents(set_documents.ids)

    @api.model
    def default_get(self, fields_list):
        res = super(CustomSearchDocumentWizard, self).default_get(fields_list)
        menu_portal_request = self.env.context.get('menu_portal_request', False)
        if bool(menu_portal_request):
            user = self.env.uid
            res['partner_id'] = self.env['res.users'].browse(user).parent_id.id

        res['filtered_domain'] = True
        return res

    @api.onchange('filtered_domain')
    def onchange_filtered_domain(self):
        domain = [('type', '=', 'product')]
        if bool(self.portal_request_id):
            peticionario = self.portal_request_id.peticionario_partner_id
        elif bool(self.env.user.partner_id and self.env.user.partner_id.peticionario):
            peticionario = self.env.user.partner_id
        else:
            peticionario = False

        if bool(peticionario) and bool(peticionario.parent_id):
            documents = self.env['product.template'].sudo().browse(peticionario.parent_id.allowed_product_tmpl_ids_getter).exists().mapped("product_variant_ids.almc_producto_id").ids
            domain.append(('id', 'in', documents))
        return {
            'domain': {
                'product_ids': domain
                }
            }

