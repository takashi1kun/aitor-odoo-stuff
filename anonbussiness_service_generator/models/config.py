# -*- coding: utf-8 -*-
# (c) 2019 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    conductor_por_defecto = fields.Many2one('res.partner', required=True, string='Conductor')
    ayudante_por_defecto = fields.Many2one('res.partner', required=True, string='Ayudante')
    kilometros_por_hora = fields.Integer(required=True, string='Kilometros por Hora')
    kilometros_por_jornada = fields.Integer(required=True, string='Kilometros por Jornada')
    kilometros_extra_producto_defecto_id = fields.Many2one('product.product', required=True,
                                                           string='Producto para kilometros extra')
    horas_extra_producto_defecto_id = fields.Many2one('product.product', required=True,
                                                           string='Producto para horas extra')
    km_uom_id = fields.Many2one('product.uom', required=True,
                                                           string='Unidad de medida KILOMETROS')
    hr_uom_id = fields.Many2one('product.uom', required=True,
                                                           string='Unidad de medida HORAS')
    jornada_uom_id = fields.Many2one('product.uom', required=True,
                                string='Unidad de medida JORNADA')
    direccion_uom_id = fields.Many2one('product.uom', required=True,
                                string='Unidad de medida DIRECCION')
    turno_noche_product_id = fields.Many2one("product.product")
    producto_extra_lluvia_km_id = fields.Many2one("product.product")
    producto_extra_lluvia_direccion_id = fields.Many2one("product.product")
    producto_extra_peaje_id = fields.Many2one("product.product")
    producto_minutos_espera_moto_id = fields.Many2one("product.product", string='Producto Minutos Espera de Moto')
    producto_minutos_espera_coche_id = fields.Many2one("product.product", string='Producto Minutos Espera de Coche')
    extra_direcciones_id = fields.Many2one("product.product")
    tax_for_peaje_id = fields.Many2one("account.tax")
    porcentaje_turno_noche = fields.Float()
    empieza_nocturnidad = fields.Float()
    acaba_nocturnidad = fields.Float()
    tiempo_disponible_carga_y_descarga = fields.Float()
    extra_festividad_id = fields.Many2one('product.product', required=True, string='Producto para Extra Festividad')
    porcentaje_festividad = fields.Float()
    producto_seguro_limite_responsabilidad_id = fields.Many2one("product.product", string='Producto Seguro Limite de Responsabilidad')

    @api.multi
    def param(self, param, is_float=False, default=""):
        val = self.env['ir.config_parameter'].get_param(param, default=None)
        if is_float:
            return float(val) if val else None
        else:
            return int(val) if val else None
        
    @api.multi
    def set_param(self, param, value):
        self.ensure_one()
        self.env['ir.config_parameter'].set_param(param, value)
        
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            conductor_por_defecto=self.param('default_driver_id', default=None),
            ayudante_por_defecto=self.param('default_helper_id', default=None),
            kilometros_por_hora=self.param('kilometros_por_hora', default=0),
            kilometros_por_jornada=self.param('kilometros_por_jornada', default=0),
            kilometros_extra_producto_defecto_id=self.param('kilometros_extra_producto_defecto_id', default=None),
            horas_extra_producto_defecto_id=self.param('horas_extra_producto_defecto_id', default=None),
            km_uom_id=self.param('km_uom_id', default=None),
            hr_uom_id=self.param('hr_uom_id', default=None),
            direccion_uom_id=self.param('direccion_uom_id', default=None),
            jornada_uom_id=self.param('jornada_uom_id', default=None),
            producto_extra_lluvia_km_id=self.param('producto_extra_lluvia_km_id', default=None),
            producto_extra_lluvia_direccion_id=self.param('producto_extra_lluvia_direccion_id', default=None),
            producto_extra_peaje_id=self.param('producto_extra_peaje_id', default=None),
            producto_minutos_espera_moto_id=self.param('producto_minutos_espera_moto_id', default=None),
            producto_minutos_espera_coche_id=self.param('producto_minutos_espera_coche_id', default=None),
            turno_noche_product_id=self.param('turno_noche_product_id', default=None),
            tax_for_peaje_id=self.param('tax_for_peaje_id', default=None),
            extra_direcciones_id=self.param('extra_direcciones_id', default=None),
            porcentaje_turno_noche=self.param('porcentaje_turno_noche', is_float=True, default=0.0),
            porcentaje_festividad=self.param('porcentaje_festividad', is_float=True, default=0.0),
            empieza_nocturnidad=self.param('empieza_nocturnidad', is_float=True, default=0.0),
            acaba_nocturnidad=self.param('acaba_nocturnidad', is_float=True, default=0.0),
            tiempo_disponible_carga_y_descarga=self.param('tiempo_disponible_carga_y_descarga', is_float=True, default=0.0),
            extra_festividad_id=self.param('extra_festividad_id', default=None),
            producto_seguro_limite_responsabilidad_id=self.param('producto_seguro_limite_responsabilidad_id', default=None)
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.set_param('default_driver_id', self.conductor_por_defecto.id)
        self.set_param('default_helper_id', self.ayudante_por_defecto.id)
        self.set_param('extra_direcciones_id', self.extra_direcciones_id.id)
        self.set_param('kilometros_por_hora', self.kilometros_por_hora)
        self.set_param('kilometros_por_jornada', self.kilometros_por_jornada)
        self.set_param('km_uom_id', self.km_uom_id.id)
        self.set_param('hr_uom_id', self.hr_uom_id.id)
        self.set_param('jornada_uom_id', self.jornada_uom_id.id)
        self.set_param('producto_extra_lluvia_km_id', self.producto_extra_lluvia_km_id.id)
        self.set_param('producto_extra_lluvia_direccion_id', self.producto_extra_lluvia_direccion_id.id)
        self.set_param('tax_for_peaje_id', self.tax_for_peaje_id.id)
        self.set_param('producto_extra_peaje_id', self.producto_extra_peaje_id.id)
        self.set_param('producto_minutos_espera_moto_id', self.producto_minutos_espera_moto_id.id)
        self.set_param('producto_minutos_espera_coche_id', self.producto_minutos_espera_coche_id.id)
        self.set_param('kilometros_extra_producto_defecto_id', self.kilometros_extra_producto_defecto_id.id)
        self.set_param('direccion_uom_id', self.direccion_uom_id.id)
        self.set_param('horas_extra_producto_defecto_id', self.horas_extra_producto_defecto_id.id)
        self.set_param('turno_noche_product_id', self.turno_noche_product_id.id)
        self.set_param('porcentaje_turno_noche', self.porcentaje_turno_noche)
        self.set_param('porcentaje_festividad', self.porcentaje_festividad)
        self.set_param('empieza_nocturnidad', self.empieza_nocturnidad)
        self.set_param('acaba_nocturnidad', self.acaba_nocturnidad)
        self.set_param('tiempo_disponible_carga_y_descarga', self.tiempo_disponible_carga_y_descarga)
        self.set_param('extra_festividad_id', self.extra_festividad_id.id)
        self.set_param('producto_seguro_limite_responsabilidad_id', self.producto_seguro_limite_responsabilidad_id.id)


