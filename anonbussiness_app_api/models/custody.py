# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo import exceptions
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    custody_level_name = fields.Char(related="custody_level_id.name")
    custody_level = fields.Integer(related="custody_level_id.level")

    @api.multi
    def getPrefixes(self, mapped=False):
        records = self.sudo().read([
            "type",
            "default_code",
            "custody_level_id",
            "custody_level",
            "custody_level_name"
        ])
        filtered = filter(lambda record: record["type"] == "product" and bool(record["default_code"]),records)
        mapped_records = map(lambda record:{
            "prefix": record["default_code"],
            "type": record["custody_level_name"],
            "level": record["custody_level"],
            "levelId": record["custody_level_id"][0]
        }, filtered)
        return mapped_records if mapped else list(mapped_records)

class ProductProduct(models.Model):
    _inherit = "product.product"

    custody_level_name = fields.Char(related="custody_level_id.name")
    custody_level = fields.Integer(related="custody_level_id.level")

    @api.multi
    def getPrefixes(self, mapped=False):
        records = self.sudo().read([
            "type",
            "default_code",
            "custody_level_id",
            "custody_level",
            "custody_level_name"
        ])
        filtered = filter(lambda record: record["type"] == "product" and bool(record["default_code"]),records)
        mapped_records = map(lambda record:{
            "prefix": record["default_code"],
            "type": record["custody_level_name"],
            "level": record["custody_level"],
            "levelId": record["custody_level_id"][0]
        }, filtered)
        return mapped_records if mapped else list(mapped_records)

class CustodyCaseLevel(models.Model):
    _inherit = "custody.case.level"

    @api.multi
    def parseAppMulti(self, mapped=False):
        records = self.sudo().read(["name", "level", "id", "product_ids"])
        themap =map(lambda x: {
            "type": x["name"],
            "level": x["level"],
            "id": x["id"],
            "prefixes": self.env["product.product"].sudo().browse(x["product_ids"]).getPrefixes()
        }, records)
        return themap if mapped else list(themap)

    @api.multi
    def parseApp(self):
        self.ensure_one()
        return {
            "type": self.name,
            "level": self.level,
            "id": self.id,
            "prefixes": self.product_ids.getPrefixes()
        }

    @api.multi
    def getPosiblePrefixes(self):
        """
        If called on a single record it gives its products prefixes, if multiple records, the collective product
        prefixes of all records and in the case of no record, the collective product prefixes of all levels
        :return:
        """
        if len(self) == 1:
            products = self.product_ids
        elif len(self) > 1:
            products = self.mapped("product_ids")
        else:
            products = self.search([]).mapped("product_ids")
        return products.getPrefixes()


class CustodyDocument(models.Model):
    _inherit = "custody.document"

    # parent_chain_ids_string = fields.Char(compute="_compute_parent_chain_ids_string", store=True)

    @property
    @api.multi
    def parent_chain_ids(self):
        self.ensure_one()
        if not self.owner_id or not self.parent_cadena:
            return []
        # return list(map(int,self.parent_chain_ids_string.split(","))) if self.parent_chain_ids_string else []
        chain_names = self.parent_chain_names
        parent_names_len = len(chain_names)
        return self.get_parents_by_number(parent_names_len,chain_names)

    @property
    @api.multi
    def parents_ordered_map(self):
        self.ensure_one()
        suself = self.sudo()
        return map(lambda id: suself.browse([id]),suself.parent_chain_ids)


    @property
    @api.multi
    def parent_chain_names(self):
        self.ensure_one()
        if self.parent_cadena:
            return self.parent_cadena.split(" > ")
        else:
            return []

    @api.multi
    def get_parents_by_number(self,number,chain_names):
        self.ensure_one()
        if number == 0:
            return []
        elif number == 1:
            return [self.parent_id.id]
        elif number == 2:
            return [self.max_parent_id.id, self.parent_id.id]
        elif number == 3:
            return [self.max_parent_id.id, self.max_hijo_parent_id.id, self.parent_id.id]
        else:
            return self.get_parents_by_chain(chain_names)

    @api.multi
    def get_parents_by_chain(self, chain_names_list):
        self.ensure_one()
        if len(chain_names_list) < 4 or not self.owner_id:
            raise Exception("Has to have at least 4 parents")
        owner_id = self.owner_id.id
        reduced_list = chain_names_list[2:-1]
        reduced_list_len = len(reduced_list)
        search_result = self.sudo().search([
            ("name", "in", reduced_list) if reduced_list_len > 1 else ("name", "=", reduced_list[0]),
            ("owner_id", "=", owner_id)
        ])
        if reduced_list_len == 1:
            return [self.max_parent_id.id, self.max_hijo_parent_id.id, search_result.id, self.parent_id.id]
        search_result_read = search_result.read(["id", "name"])
        parent_ids = [self.max_parent_id.id, self.max_hijo_parent_id.id]
        for parent in search_result_read:
            parent_name = parent["name"]
            for name in reduced_list:
                if parent_name == name:
                    parent_ids.append(parent["id"])
                    break
        parent_ids.append(self.parent_id.id)
        return parent_ids

    #@api.multi
    #@api.depends('parent_cadena','owner_id')
    def _compute_parent_chain_ids_string(self):
        for this in self:
            if this.parent_cadena and this.owner_id:
                parents = this.parent_chain_names
                if parents and len(parents):
                    # print("procesando %s con id %s ID" % (this.name, str(this.id)))
                    parent_len = len(parents)
                    parent_ids = this.get_parents_by_number(parent_len, parents)
                    this.parent_chain_ids_string = ",".join(map(str,parent_ids))
                    # if parent_len == 1:
                    #     this.parent_chain_ids_string = ",".join(map(lambda parent: str(parent.id),[this.parent_id]))
                    # elif parent_len == 2:
                    #     this.parent_chain_ids_string = ",".join(map(lambda parent: str(parent.id),[this.max_parent_id, this.parent_id]))
                    # elif parent_len == 3:
                    #     this.parent_chain_ids_string = ",".join(map(lambda parent: str(parent.id),[this.max_parent_id, this.max_hijo_parent_id, this.parent_id]))
                    # else:
                    #     this.parent_chain_ids_string = ",".join([
                    #             *list(map(lambda parent: str(parent.id),[this.max_parent_id, this.max_hijo_parent_id])),
                    #             *(list(map(lambda parent: str(self.sudo().search([("name", "=", parent),("owner_id", "=", this.owner_id.id)], limit=1).id),parents[2:-1]))),
                    #             str(this.parent_id.id)
                    #         ])
                else:
                    this.parent_chain_ids_string = ""
            else:
                this.parent_chain_ids_string = ""

    @api.multi
    def getFechaDestruccionYear(self):
        self.ensure_one()
        if self.fecha_destruccion_prevista:
            date = self.fecha_destruccion_prevista
            datetime = fields.Datetime()
            rDate = datetime.from_string(date)
            return rDate.year
        else:
            return False

    @property
    @api.multi
    def fecha_recepcion_container(self):
        self.ensure_one()
        return self.max_parent().fecha_recepcion

    @property
    @api.multi
    def all_tree_ids(self):
        return self.browse(self._all_tree_ids_gen)

    @property
    @api.multi
    def _all_tree_ids_gen(self):
        ids = set(self.ids)
        childs = self.mapped("contenido_ids")
        if len(childs) != 0:
            ids.update(childs._all_tree_ids_gen)
        return ids

    @api.multi
    def generateDatesForAPP(self):
        for this in self:
            if not this.fecha_inventario:
                this.fecha_inventario = fields.Date.today()
            if not this.fecha_recepcion:
                this.fecha_recepcion = this.fecha_recepcion_container

    @api.multi
    def getTreeForApp(self, stockMove, isTop=True, fullTree=True):
        _logger.debug("LOG TREE API 1")
        ProductProduct = self.env["product.product"].sudo()
        CustodyDocument = self.env["custody.document"].sudo()
        res = []
        level = stockMove.picking_id.task_id.sale_line_id.order_id.unidad_recepcion_id.level
        _logger.debug("LOG TREE API 2")
        records = self.sudo().read([
            "product_id",
            "codigo_identificador",
            "is_etiqueta_externa",
            "etiqueta",
            "id",
            "contenido_ids",
            "parent_id",
            "is_indeterminado"
        ])
        _logger.debug("LOG TREE API 3")
        _logger.debug(len(records))
        _logger.debug(records[0])
        _logger.debug(records[1])
        _logger.debug(records[2])
        _logger.debug(records[3])
        _logger.debug(records[4])
        _logger.debug(records[5])
        for record in records:
            _logger.debug("LOG TREE API 4")
            product_id = ProductProduct.browse([record["product_id"][0]])
            if not record["is_indeterminado"] and level <= product_id.custody_level_id.level:
                contenido_ids = CustodyDocument.browse(record["contenido_ids"])
                parent_id = CustodyDocument.browse([record["parent_id"][0]])
                parsed_app = product_id.custody_level_id.parseAppMulti()
                res.append({
                    "type": parsed_app,
                    "anonbussinessCode": record["id"].codigo_identificador or '',
                    "barcode": record["etiqueta"] or '' if not record["is_etiqueta_externa"] else record["etiqueta"] or record["codigo_identificador"] or '',
                    "documentId": record["id"],
                    "stockMoveId": stockMove.id,
                    "isTop": isTop,
                    "isBottom": bool(len(record["contenido_ids"])),
                    "isParentTop": not parent_id.parent_id,
                    "productType": parsed_app,
                    "childs": contenido_ids.getTreeForApp(stockMove, isTop=False) if fullTree else []
                })
        # for this in filter(lambda doc: not doc.is_indeterminado and level <= doc.product_id.custody_level_id.level, self):
        #     res.append({
        #         "type": this.product_id.custody_level_id.parseApp(),
        #         "anonbussinessCode": this.codigo_identificador or '',
        #         "barcode": this.etiqueta or '' if not this.is_etiqueta_externa else this.etiqueta or this.codigo_identificador or '',
        #         "documentId": this.id,
        #         "stockMoveId": stockMove.id,
        #         "isTop": isTop,
        #         "isBottom": bool(len(this.contenido_ids)),
        #         "isParentTop": not this.parent_id.parent_id,
        #         "productType": this.product_id.custody_level_id.parseApp(),
        #         "childs": this.contenido_ids.getTreeForApp(stockMove, isTop=False) if fullTree else []
        #     })
        if isTop:
            return res[0]
        else:
            return res

    @api.multi
    def getAllMyParentsForTheApp(self, invert=True, initialStep=True):
        self.ensure_one()
        res = []
        if self.parent_id:
            res.append(self.parent_id)
            parentData = self.parent_id.getAllMyParentsForTheApp(initialStep=False)
            res.extend(parentData)
            if invert and initialStep:
                res.reverse()
            return res
        else:
            return []

    @api.multi
    def createNewContenidoAppTask(self, childs):
        self.ensure_one()
        print(childs)
        product_obj = self.env['product.product']
        doc_obj = self.env['custody.document']

        for child in childs:
            manual = child.get('manual', False)
            externa = child.get('isEtiquetaExterna', False)
            if manual:
                codigo_identificador = child['anonbussinessCode']
                etiqueta = False
            elif externa:
                codigo_identificador = child['barcode']
                etiqueta = False
            else:
                codigo_identificador = child['anonbussinessCode']
                etiqueta = child['barcode']

            write_vals = {
                'is_etiqueta_externa': bool(externa),
                'codigo_identificador': codigo_identificador,
                'etiqueta': etiqueta,
                'referencia_cliente': child['archivistaData']['refClient'],
                'descripcion': child['archivistaData']['description'],
                'tramo_desde': child['archivistaData']['from'],
                'tramo_hasta': child['archivistaData']['to'],
            }
            year = child['archivistaData'].get('year', False)
            if year:
                write_vals.update({'year_desde': year, 'year_hasta': year})

            product_code = child['prefix']['prefix']
            product_level = child['prefix']['level']
            product = product_obj.search([("custody_level_id.level", "=", product_level), ('type', '=', 'product'), ('default_code', '=', product_code)])

            write_vals.update({
                'product_id': product.id,
                'parent_id': self.id,
                'owner_id': self.owner_id.id,
                'location_id': self.location_id.id,
                'task_inventario_id': self.task_inventario_id.id,
                'tarea_inventario': self.tarea_inventario,
                'custodia_state': "draft",
            })

            buscar = [('owner_id', '=', self.owner_id.id), ('codigo_identificador', '=', child['anonbussinessCode']), ('product_id', '=', product.id), ('task_inventario_id', '=', self.task_inventario_id.id)]
            mis_repes = doc_obj.search(buscar)
            if bool(mis_repes):
                relation = mis_repes.mapped('document_relation_id')
                if not bool(relation):
                    relation_vals = {'name': child['anonbussinessCode'], 'owner_id': self.owner_id.id}
                    relation = relation.create(relation_vals)
                    mis_repes.write({'document_relation_id': relation.id})
                write_vals.update({'document_relation_id': relation.id})

            docId = child.get("documentId", 0)
            if docId < 1:
                doc = doc_obj.create(write_vals)
            else:
                doc = doc_obj.browse([docId])
                if doc:
                    doc.update(write_vals)
                else:
                    doc = doc_obj.create(write_vals)

            doc_obj += doc

            nietos = child.get('childs', False)
            if bool(nietos):
                new_docs = doc.createNewContenidoAppTask(nietos)

        return doc_obj


