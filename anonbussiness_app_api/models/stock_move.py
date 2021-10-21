# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import ValidationError

import collections.abc


class JuspayObject:
    def __init__(self, response):
        # don't use self.__dict__ here
        self._response = response

    def __getitem__(self, key):
        return self.advanced_get(key)

    def __getattr__(self, key):
        return self.advanced_get(key)

    def advanced_get(self, key):
        res = self.get(key)
        if type(res) in (dict, list, map):
            return self.__class__(res)
        else:
            return res

    def get(self, key):
        steps = key.split(".")
        res = self._response
        for step in steps:
            if type(res) == list:
                res = list(map(lambda x: x.get(step, False) if x else False, res))
            else:
                res = res.get(step, False)
                if not res:
                    break
        return res

    def __repr__(self):
        return str(self._response)


class StockLocationChain:
    def __init__(self, loc, doc, chain=[]):
        self.location = loc
        self.chain = chain
        self.document = doc


def dict_merge(*args, add_keys=True):
    assert len(args) >= 2, "dict_merge requires at least two dicts to merge"
    rtn_dct = args[0].copy()
    merge_dicts = args[1:]
    for merge_dct in merge_dicts:
        if add_keys is False:
            merge_dct = {key: merge_dct[key] for key in set(rtn_dct).intersection(set(merge_dct))}
        for k, v in merge_dct.items():
            if not rtn_dct.get(k):
                rtn_dct[k] = v
            elif k in rtn_dct and type(v) != type(rtn_dct[k]):
                raise TypeError("Error De Tipado")
            elif isinstance(rtn_dct[k], dict) and isinstance(merge_dct[k], collections.abc.Mapping):
                rtn_dct[k] = dict_merge(rtn_dct[k], merge_dct[k], add_keys=add_keys)
            elif isinstance(v, list):
                for list_value in v:
                    if list_value not in rtn_dct[k]:
                        rtn_dct[k].append(list_value)
            else:
                rtn_dct[k] = v
    return rtn_dct


class StockMove(models.Model):
    _inherit = "stock.move"

    @property
    @api.multi
    def dest_location_unknown(self):
        self.ensure_one()
        return not bool(self.location_dest_id) or self.location_dest_id.usage not in ('internal', 'transit')

    @api.multi
    def handleNewUbication(self, string, query="barcode"):
        self.ensure_one()
        ubication = self.env["stock.location"].search([(query, "=", string)], limit=1)
        if ubication:
            self.location_dest_id = ubication.id
            self.document_move_location_id = ubication.id
            self.document_id.location_id = ubication.id
            return True
        else:
            return False

    @api.multi
    def forceConfirm(self):
        self.filtered(lambda move: move.state == 'draft')._action_confirm(merge=False, merge_into=False)
        self._action_assign()
        for this in self:
            qty_already_done = float(sum(this.move_line_ids.mapped("qty_done")))
            prev_move_lines = this.move_line_ids
            prev_move_lines.sudo().write({
                'picking_id': this.picking_id.id,
                'move_id': this.id,
                'product_id': this.product_id.id,
                'product_uom_id': this.product_uom.id,
                'qty_done': this.product_qty if qty_already_done == 0.0 else this.product_qty - qty_already_done,
                'location_id': this.location_id.id,
                'location_dest_id': this.location_dest_id.id,
            })
        self._action_done()

    @staticmethod
    def forEach(value, function):
        return list(map(function, value))

    @api.multi
    def parseMyChain(self):
        self.ensure_one()
        return self.document_id.parents_ordered_map
        #parent_ids = map(lambda x: self.sudo().browse([int(x)]), self.document_id.parent_chain_ids_string.split(","))
        #return parent_ids
        # return list(map(int ,self.document_id.parent_chain_ids_string.split(",")))
        # chain = self.document_id.parent_cadena
        #owner_id = self.document_id.owner_id.id
        #docModel = self.env["custody.document"]
        #parents = chain.split(" > ")
        #return self.forEach(parents, lambda parent: docModel.search([
        #    ("name", "=", parent),
        #    ("owner_id", "=", owner_id)
        #], limit=1))

    @api.multi
    def parseMyParents(self):
        self.ensure_one()
        chain = self.parent_cadena
        stock_documents = self.forEach(
            self.forEach(
                chain.splitlines(),
                lambda x: self.forEach(
                    x.split(" > "),
                    lambda y: self.env["custody.document"].search([
                        ("codigo_identificador", "=", y)
                    ], limit=1)
                )
            ),
            lambda z: StockLocationChain(z[0].location_id, self.document_id, z)
        )
        # FORMATO:
        #  barcodegrandparent > barcodeparent\n
        #  barcodegrandparent2 > barcodeparent2
        #  ===
        # [
        #   StockLocationChain = (
        #       document: custody.document(currentDocument)
        #       location: stock.location(barcodegrandparentlocation)
        #       chain: [custody.document(barcodegrandparent), custody.document(barcodeparent)]
        #   ),
        #   StockLocationChain = (
        #       document: custody.document(currentDocument)
        #       location: stock.location(barcodegrandparent2location)
        #       chain: [custody.document(barcodegrandparent2), custody.document(barcodeparent2)]
        #    ),
        # ]
        #
        return stock_documents

    @api.multi
    def getAltramo(self):
        self.ensure_one()
        inserto_lines = self.picking_id.task_id.sale_service_ids
        document = self.document_id
        if not inserto_lines:
            return False
        iLine = inserto_lines.filtered(lambda line: line.document_id.id == document.id and bool(line.document_id))
        if iLine:
            return iLine.al_tramo if len(iLine) == 1 else False
        else:
            return False

    @api.multi
    def getBarcodeForApp(self, externa=True, chorizo=False):
        self.ensure_one()
        if chorizo and not self.getAltramo() and not self.document_id.is_etiqueta_externa and not bool(self.etiqueta):
            return self.codigo_identificador or ""
        elif externa and not bool(self.etiqueta) and self.document_id.is_etiqueta_externa:
            return self.codigo_identificador or ""
        else:
            return self.etiqueta or ""

    @api.multi
    def getPosition(self):
        return self.mapped(lambda this: {
            "id": int(this.id),
            "product": {
                "name": this.product_id.name,
                "type": this.product_id.custody_level_id.name,
                "level": this.product_id.custody_level_id.level,
                "prefix": this.product_id.default_code
            },
            "amount": this.product_uom_qty,
            "document": {
                "anonbussinessCode": this.codigo_identificador or '',
                "barcode": this.getBarcodeForApp(chorizo=True),
                "clientReference": this.referencia_cliente or ''
            },
            "container": {
                "anonbussinessCode": this.document_max_parent_codigo or '',
                "barcode": this.document_max_parent_etiqueta or this.document_max_parent_codigo or '',
                "clientReference": this.document_id.max_parent_id.referencia_cliente or ''
            },
            "chain": this.document_id.parent_cadena or '',
            "supportBarcode": this.document_max_hijo_parent_etiqueta or '',
            "ubication": this.document_move_location_id.getLocationDataTab(limit=1) or '',
            "location": {
                "name": this.document_move_location_id.name or '',
                "barcode": this.document_move_location_id.barcode or '',
                "oldcode": this.document_move_location_id.old_barcode or '',
                "hasoldcode": this.document_move_location_id.wh_old_barcode,
                "parentDocuments": self.forEach(this.parseMyChain(), lambda parent: {
                    "anonbussinessCode": parent.codigo_identificador or '',
                    "barcode": parent.etiqueta or '',
                    "clientReference": parent.referencia_cliente or '',
                    "product": {
                        "name": parent.product_id.name,
                        "type": parent.product_id.custody_level_id.name,
                        "level": parent.product_id.custody_level_id.level
                    }
                } if parent.exists() else {
                    "anonbussinessCode": '',
                    "barcode": '',
                    "clientReference": '',
                    "product": {
                        "name": '',
                        "type": '',
                        "level": 0
                    }
                }) if this.document_id.parent_cadena else []
            }
        })

    @api.multi
    def getLineModelD(self):
        res = []
        for this in self:
            this.product_id.custody_level_id.name
            json = this.getLineDataTab(chorizo=False)[0]
            json = dict_merge(json, {
                "multiUbications": this.inserto_id.al_tramo,
                "multiUbicationsKey": this.document_id.codigo_identificador if this.inserto_id.al_tramo else "",
                "name": this.document_id.codigo_identificador if this.inserto_id.al_tramo else this.product_id.custody_level_id.name + " " + (
                            this.document_id.codigo_identificador or this.document_id.etiqueta),
                "extractionData": {
                    "ubication": this.document_move_location_id.getLocationDataTab(limit=1),
                    "containers": self.forEach(this.document_id.getAllMyParentsForTheApp(), lambda document: {
                        "type": document.product_id.custody_level_id.parseApp(),
                        "anonbussinessCode": document.codigo_identificador or '',
                        "barcode": document.etiqueta or ''
                    })
                }
            })
            res.append(json)
        return res

    @api.multi
    def getTreeModelE(self, fullTree=True):
        res = []
        for this in self:
            res.append(this.document_id.getTreeForApp(this, fullTree=fullTree))
        return res

    @api.multi
    def getLineDataTab(self, chorizo=False):
        record_map = map(lambda record:{
                **record,
                "product": {
                    "name": record["product_id"][1],
                    "id": record["product_id"][0],
                    "custody_level_id": self.env["product.product"].sudo().browse([record["product_id"][0]]).custody_level_id.read(["name","level"])
                },
                "document_move_location": self.env["stock.location"].sudo().browse([record["document_move_location_id"][0]]),
                "document":self.env["custody.document"].sudo().browse([record["document_id"][0]])
            } ,self.sudo().read([
                "id",
                "product_id",
                "product_uom_qty",
                "codigo_identificador",
                "referencia_cliente",
                "document_id",
                "etiqueta",
                "document_max_parent_codigo",
                "document_max_parent_etiqueta",
                "document_max_hijo_parent_etiqueta",
                "document_move_location_id"
            ]))
        def process_data_tab(record):
            this = self.sudo().browse(record["id"])
            al_tramo = this.getAltramo()
            is_etiqueta_externa = record["document"].is_etiqueta_externa
            codigo_identificador = record["codigo_identificador"]
            document_id = record["document"]
            return {
                "id": int(record["id"]),
                "product": {
                    "name": record["product"]["name"],
                    "type": record["product"]["custody_level_id"][0]["name"],
                    "level": record["product"]["custody_level_id"][0]["level"],
                    "prefix": this.env["product.product"].browse([record["product"]["id"]]).default_code
                },
                "amount": record["product_uom_qty"],
                "document": {
                    "anonbussinessCode": codigo_identificador or '',
                    "barcode": this.getBarcodeForApp(chorizo=chorizo),
                    "clientReference": record["referencia_cliente"] or '',
                    "manual": not al_tramo and not is_etiqueta_externa and bool(record["etiqueta"] or codigo_identificador),
                    "alTramo": al_tramo,
                    "isEtiquetaExterna": is_etiqueta_externa
                },
                "container": {
                    "anonbussinessCode": record["document_max_parent_codigo"] or '',
                    "barcode": record["document_max_parent_etiqueta"] or '',
                    "clientReference": document_id.max_parent_id.referencia_cliente or ''
                },
                "chain": document_id.parent_cadena or '',
                "supportBarcode": record["document_max_hijo_parent_etiqueta"] or '',
                "ubication": record["document_move_location"].getLocationDataTab(limit=1)
            }

        return list(map(process_data_tab, record_map))

    @api.multi
    def handleAppTaskRecogida(self, data_line):
        doc_obj = self.env['custody.document']

        data_line_obj = JuspayObject(data_line)
        manual = data_line.get('manual', False)
        externa = data_line.get('isEtiquetaExterna', False)
        if manual:
            codigo_identificador = data_line['anonbussinessCode']
            etiqueta = False
        elif externa:
            codigo_identificador = data_line['barcode']
            etiqueta = False
        else:
            codigo_identificador = data_line['anonbussinessCode']
            etiqueta = data_line['barcode']

        tipo_soporte = data_line_obj.get("prefix.prefix")

        stock_move = data_line.get('stockMoveId', False)
        if stock_move in self.ids:
            move = self.browse(stock_move)
        else:
            move = self[0].createNewMoveAppTask(tipo_soporte)

        if not bool(etiqueta) and not bool(codigo_identificador):
            return False

        write_vals = {
            'codigo_identificador': codigo_identificador,
            'etiqueta': etiqueta,
            'referencia_cliente': data_line['archivistaData']['refClient'],
            'descripcion': data_line['archivistaData']['description'],
            'tramo_desde': data_line['archivistaData']['from'],
            'tramo_hasta': data_line['archivistaData']['to'],
        }
        year = data_line['archivistaData'].get('year', False)
        if year:
            write_vals.update({'year_desde': year})
        move.write(write_vals)

        move.move_line_ids.unlink()
        write_vals = {
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'move_id': move.id,
            'owner_id': move.owner_id.id,
            'picking_id': move.picking_id.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'qty_done': 1.0,
        }
        move.move_line_ids.create(write_vals)

        write_vals = {
            'is_etiqueta_externa': bool(externa),
            'product_id': move.product_id.id,
            'parent_id': False,
            'owner_id': move.owner_id.id,
            'location_id': move.location_id.id,
            'task_inventario_id': move.picking_id.task_id.id,
            'tarea_inventario': move.picking_id.task_id.name,
            'custodia_state': "draft",
            'referencia_cliente': move.referencia_cliente,
            'codigo_identificador': move.codigo_identificador,
            'etiqueta': move.etiqueta,
            'year_desde': move.year_desde,
            'year_hasta': move.year_desde,
            'descripcion': move.descripcion,
            'tramo_desde': move.tramo_desde,
            'tramo_hasta': move.tramo_hasta,
        }
        docId= data_line.get("documentId", 0)
        if docId < 1:
            doc = doc_obj.create(write_vals)
        else:
            doc = doc_obj.browse([docId])
            if doc:
                doc.update(write_vals)
            else:
                doc = doc_obj.create(write_vals)
        move.document_id = doc.id

        move.inserto_id.write({
            'document_id': doc.id,
            'descripcion': doc.descripcion,
            'anyo': doc.year_desde,
        })

        childs = data_line.get('childs', False)
        if bool(childs):
            new_docs = doc.createNewContenidoAppTask(childs)
            move.contenido_ids = [(6, 0, new_docs.ids)]

        print(data_line)

    @api.multi
    def createNewMoveAppTask(self, code):
        self.ensure_one()

        sale_service_obj = self.env['sale.service']
        task_material_obj = self.env['project.task.material']

        vals = [('type', '=', 'product'), ('default_code', '=', code)]
        almacenable = self.product_id.search(vals)

        vals = [('type', '=', 'consu'), ('almc_producto_id', '=', almacenable.id)]
        consumible = self.product_id.search(vals)

        picking = self.picking_id
        sale_order = picking.task_id.sale_line_id.order_id if picking.task_id.sale_line_id and picking.task_id.sale_line_id.order_id else False
        vals = {
            'owner_id': picking.owner_id.id,
            'inserto_id': consumible.id,
            'al_tramo': False,
        }
        if sale_order:
            vals = {
                'sale_id': sale_order.id,
                **vals
            }
        inserto = sale_service_obj.create(vals)

        task = picking.task_id
        vals = {'sale_service_ids': [(4, inserto.id)]}
        tareas = task.project_id.tasks.filtered(lambda x: x.serial == task.serial and not x.terminado)
        tareas.write(vals)

        vals = self.prepare_create_move(almacenable)
        vals.update({'inserto_id': inserto.id})
        move = self.create(vals)

        vals = {
            'product_id': consumible.id,
            'quantity': 1.0,
            'task_id': task.id,
            'inserto_id': inserto.id,
            'stock_move_id': move.id
        }
        material = task_material_obj.create(vals)
        for t in tareas.filtered(lambda x: x.id != task.id):
            vals = {'product_id': consumible.id, 'quantity': 1.0, 'task_id': t.id, 'inserto_id': inserto.id}
            material = task_material_obj.create(vals)

        return move


