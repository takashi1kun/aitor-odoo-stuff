# -*- encoding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    """
    Ran at module Installation.
    Changes `company_id` to False in all ProductPricelists that have it setted to a non False value.
    :param cr:
    :param registry:
    :return:
    """
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env["product.pricelist"]._clear_all_company_ids()