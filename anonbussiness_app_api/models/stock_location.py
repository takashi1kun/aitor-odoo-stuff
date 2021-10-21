# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class StockLocation(models.Model):
    _inherit = "stock.location"

    @api.multi
    def getLocationDataTab(self, limit=0):
        if not self:
            return {} if limit == 1 else []
        elif limit == 1:
            return self.locationDataTab if len(self) == 1 else self[0].locationDataTab
        elif limit == 0:
            return self.mapped(lambda x: x.locationDataTab)
        else:
            return self.mapped(lambda x: x.locationDataTab)[0:limit]
        # return (res if limit == 0 else res[0] if limit == 1 else res[0:limit]) if bool(len(self.ids)) else {}

    @property
    @api.multi
    def locationDataTab(self):
        self.ensure_one()
        return {
                "name": self.name,
                "barcode": self.barcode,
                "oldcode": self.old_barcode,
                "useoldcode": self.wh_old_barcode
            }


    default_code_prefix = fields.Char(
        'Internal Reference', related="product_id.default_code") 

    @api.multi
    def getLocationDataSpace(self):
        records = self.sudo().read(['name','barcode','old_barcode','wh_old_barcode','location_available','default_code_prefix','nave','posw','posx','posy','posz'])
        return list(map(lambda record: {
                "name": record["name"],
                "barcode": record["barcode"],
                "oldcode": record["old_barcode"],
                "useoldcode": record["wh_old_barcode"],
                'space': record["location_available"],
                'prefix': record["default_code_prefix"],
                'warehouse': record["nave"],
                'floor': record["posw"],
                'line': record["posx"],
                'branch': record["posy"],
                'index': record["posz"]
            }, records))
        res = []
        for this in self:
            res.append({
                "name": this.name,
                "barcode": this.barcode,
                "oldcode": this.old_barcode,
                "useoldcode": this.wh_old_barcode,
                'space': this.location_available,
                'prefix': this.product_id.default_code,
                'warehouse': this.nave,
                'floor': this.posw,
                'line': this.posx,
                'branch': this.posy,
                'index': this.posz
            })
        return res

    @api.model
    def getAvailableUbications(self, product_types, company_id, warehouses):
        search_query = [
            ('usage', '=', 'internal'),
            ('barcode', '!=', False),
            ('location_available', '>', 0),
            ('company_id', '=', company_id.id)
        ]
        if warehouses:
            if len(warehouses) == 1:
                search_query.append(('nave_id', '=', warehouses.id))
            else:
                search_query.append(('nave_id', 'in', warehouses.ids))
        if product_types:
            if len(product_types) == 1:
                search_query.append(('product_id', '=', product_types.id))
            else:
                search_query.append(('product_id', 'in', product_types.ids))

        return self.sudo().search(search_query).getLocationDataSpace()

