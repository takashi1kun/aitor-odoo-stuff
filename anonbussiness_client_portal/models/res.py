# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    computed_address_name = fields.Char(compute="compute_address_name")
    allowed_product_tmpl_ids = fields.Many2many(comodel_name="product.template",
                                           relation="rel_portal_product_template_res_partner", column1="product_tmpl_id",
                                           column2="partner_id",compute="compute_allowed_product_tmpl_ids", store=True, compute_sudo=True)

    @property
    @api.multi
    def all_parent_ids_internal(self):
        self.ensure_one()
        if self.parent_id:
            return [self.parent_id.id, *self.parent_id.all_parent_ids]
        else:
            return []

    @property
    @api.multi
    def all_parent_ids(self):
        self.ensure_one()
        res_partner = self.env["res.partner"]
        if self.parent_id:
            return res_partner.browse(self.all_parent_ids_internal).exists()
        else:
            return res_partner

    @property
    @api.multi
    def allowed_product_tmpl_ids_getter(self):
        self.ensure_one()
        product_tmpl_ids = self.sudo().mapped("property_product_pricelist.item_ids.product_tmpl_id").ids
        product_tmpl_ids = [*product_tmpl_ids,*self.sudo().mapped("property_product_pricelist.item_ids.product_id.product_tmpl_id").ids]
        return product_tmpl_ids

    @property
    @api.multi
    def all_parents_allowed_product_tmpl_ids_getter(self):
        self.ensure_one()
        product_ids = [*self.allowed_product_tmpl_ids_getter]
        all_parents = self.all_parent_ids
        for parent_partner_id in all_parents:
            product_ids = [*product_ids, *parent_partner_id.allowed_product_tmpl_ids_getter]
        return list(set(product_ids))

    @api.multi
    @api.depends("property_product_pricelist", "property_product_pricelist.item_ids", "property_product_pricelist.item_ids.product_id", "property_product_pricelist.item_ids.product_id.product_tmpl_id", "property_product_pricelist.item_ids.product_tmpl_id")
    def compute_allowed_product_tmpl_ids(self):
        for this in self:
            product_tmpl_ids = this.sudo().mapped("property_product_pricelist.item_ids.product_tmpl_id").ids
            product_tmpl_ids = [*product_tmpl_ids,*this.sudo().mapped("property_product_pricelist.item_ids.product_id.product_tmpl_id").ids]
            this.allowed_product_tmpl_ids = [(6,0, product_tmpl_ids)]

    @api.depends(lambda self: self._display_address_depends())
    def compute_address_name(self):
        for partner in self:
            partner.computed_address_name = partner._display_address(without_company=True)


class ResGroups(models.Model):
    _inherit = "res.groups"

    user_action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.")


class ResUsers(models.Model):
    _inherit = "res.users"

    computed_action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.", compute="_computed_action_id")

    portal_user_parent_company_partner_id = fields.Many2one("res.partner", compute="_compute_portal_user_parent_company_partner_id")


    @api.multi
    @api.depends("partner_id","groups_id","partner_id.parent_id")
    def _compute_portal_user_parent_company_partner_id(self):
        for this in self.sudo():
            if len(this.groups_id.filtered(lambda x: x.is_portal)) and this.partner_id and this.partner_id.parent_id:
                this.portal_user_parent_company_partner_id = this.partner_id.parent_id.id
            else:
                this.portal_user_parent_company_partner_id = False

    @api.model
    def _search_portal_user_parent_company_partner_id(self, operator, value):
        pass

    @api.multi
    @api.depends("groups_id","action_id")
    def _computed_action_id(self):
        for this in self:
            this.computed_action_id = this._get_action_id

    @property
    @api.multi
    def _get_action_id(self):
        self.ensure_one()
        if self.action_id:
            return self.action_id
        else:
            mapped_group_actions = self.groups_id.filtered(lambda g: g.user_action_id).mapped("user_action_id")
            if len(mapped_group_actions):
                return mapped_group_actions[0]
            else:
                return self.action_id
