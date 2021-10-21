# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import ValidationError

import collections.abc
# import cProfile
#
# def profileit(name):
#     def inner(func):
#         def wrapper(*args, **kwargs):
#             prof = cProfile.Profile()
#             retval = prof.runcall(func, *args, **kwargs)
#             prof.dump_stats(name)
#             return retval
#         return wrapper
#     return inner

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


class StockPicking(models.Model):
    _inherit = "stock.picking"

    task_in_progress_in_app = fields.Boolean("Tarea en Progreso en APP", default=False)
    task_has_saved_data_in_app = fields.Boolean("Tarea tiene datos guardados en APP", default=False)
    task_saved_data_in_app = fields.Text("Datos de la Tarea en APP", default="")

    @api.multi
    def getAllUsedAnonBussinessAndBarcodes(self):
        self.ensure_one()
        levels = self.env["custody.case.level"].search([
            ("level", "<=", self.task_id.project_id.unidad_archivado_id.level)
        ]) if self.getIfCanEditData() else self.env["custody.case.level"].search([
            ("level", "<=", self.mapped("move_lines.product_id.custody_level_id.level")[0])
        ])
        documentObj = self.env["custody.document"]
        res = []
        for level in levels:
            documents = documentObj.search([
                ("product_id.custody_level_id", "=", level.id),
                ("owner_id", "=", self.owner_id.id)
            ])
            res.append({
                "level": level.level,
                "anonbussinessCodes": documents.mapped("codigo_identificador"),
                "barcodes": documents.mapped("etiqueta")
            })
        return res

    @api.multi
    def handleAppTaskFinishA(self):
        self.ensure_one()
        #self.action_assign()
        self.move_lines.forceConfirm()
        self.action_done()
        self.task_id.action_terminar()

    @api.multi
    def handleAppTaskFinishB(self, data):
        self.ensure_one()
        # interface MiniStockMove {
        #   id: number,
        #   status: MiniStockMoveStatus;
        #   isUnknown: boolean;
        #   productName: string;
        #   barcode: string;
        #   productType: string;
        # }
        # type MiniStockMoveStatus = "scanned" | "toScan" | "unknown";
        moves = self.env["stock.move"]
        for miniStockMove in data:
            move = self.filterLinesByIDs(miniStockMove['id'])
            if miniStockMove['status'] == "scanned":
                if miniStockMove['isUnknown']:
                    code = miniStockMove['barcode']
                    move.etiqueta = code
                    move.document_id.etiqueta = code
                    if not move.codigo_identificador:
                        move.codigo_identificador = code
                        move.document_id.codigo_identificador = code
                moves += move
        moves.forceConfirm()
        self.task_id.action_terminar()

    @api.multi
    def handleAppTaskFinishC(self, data):
        self.ensure_one()
        # interface StockMoveState {
        #   move: StockMovePosition;
        #   ubicationBarcode: string;
        #   scanned: boolean;
        #   isUnknown: boolean;
        #   newLocationBarcode: string;
        #   isOldCode: boolean;
        # };
        incidentar = False
        moves = self.env["stock.move"]
        for moveStateDic in data:
            moveState = JuspayObject(moveStateDic)
            move = self.filterLinesByIDs(moveState.move.id)
            if moveState.scanned:
                if moveState.isUnknown:
                    query_type = "old_barcode" if moveState.isOldCode else "barcode"
                    res = move.handleNewUbication(moveState.newLocationBarcode, query=query_type)
                    if not res:
                        incidentar = True
                moves += move
        moves.forceConfirm()
        if incidentar:
            self.appIncidentar(title="No se han encontrado ubicaciones", message="Ha habido un problema asignando ubicaciones")
        else:
            self.action_done()
            self.task_id.action_terminar()

    @api.multi
    def handleAppTaskFinishD(self, data):
        self.ensure_one()
        lines = self.move_lines
        ids_to_delete = []
        # interface StockMoveExtractionState {
        #   id:number;
        #   product: StockMoveProduct;
        #   amount: number;
        #   document: CustodyDocumentMinimal;
        #   container: CustodyDocumentMinimal;
        #   chain: string;
        #   supportBarcode: string;
        #   ubication:StockLocation;
        #   multiUbications: boolean;
        #   multiUbicationsKey: string;
        #   name: string;
        #   extractionData: StockMoveExtractionData;
        #   done: boolean;
        #   deleted: boolean;
        # }

        moves = self.env["stock.move"]
        fake_lines = False
        clear_lines = False
        fake_lines_ids = []
        for moveExtractionState in data:
            move = self.filterLinesByIDs(moveExtractionState['id'])
            if moveExtractionState["done"]:
                moves += move
            elif moveExtractionState["deleted"] and moveExtractionState["multiUbications"]:
                ids_to_delete.append(move.id)
            elif moveExtractionState["deleted"] and not moveExtractionState["multiUbications"]:
                fake_lines = True
                fake_lines_ids.append(moveExtractionState["id"])
            else:
                clear_lines = True
        if bool(len(ids_to_delete)):
            lines_to_delete = self.filterLinesByIDs(ids_to_delete)
            lines_to_not_delete = lines.filtered(lambda line: line.id not in ids_to_delete)
            anonbussiness_codes = lines_to_not_delete.mapped("codigo_identificador")
            lines_not_found = lines_to_delete.filtered(lambda line: line.codigo_identificador not in anonbussiness_codes)
            if lines_not_found:
                for line in lines_not_found:
                    self.addMessageEasy("ALERTA: Documento %s no esta en ninguna ubicacion" % line.codigo_identificador)
            lines_to_delete.handle_false_move()
        moves.forceConfirm()
        if fake_lines and not clear_lines:
            self.appIncidentar(title="Hay lineas que son falsas", message="Hay elementos en el sistema que el operario no ha encontrado en su labor",
                               affected_ids=fake_lines_ids)
        else:
            self.action_done()
            self.task_id.action_terminar()

    @api.multi
    def handleAppTaskFinishE(self, data):
        self.ensure_one()
        # interface FinishTaskDataModelE {
        #   confirmed_move_ids: number[];
        #   non_confirmed_move_ids: number[];
        #   hasNonConfirmedIds: boolean;
        # }
        if data["hasNonConfirmedIds"]:
            done = self.move_lines.filtered(lambda a: a.id in data["confirmed_move_ids"])
            done.forceConfirm()
            self.appIncidentar(title="falta algun elemento", message="Uno o varios de elementos no se ha escaneado",
                               affected_ids=data["non_confirmed_move_ids"])
        else:
            self.move_lines.forceConfirm()
            self.action_done()
            self.task_id.action_terminar()

    @api.multi
    def handleAppTaskFinishF(self, data):
        self.ensure_one()
        tree = data['tree']
        for data_line in tree:
            self.move_lines.handleAppTaskRecogida(data_line)
        top_docs = self.move_lines.mapped('document_id')
        top_docs.all_tree_ids.generateDatesForAPP()
        res = self.button_validate()
        if bool(res) and isinstance(res, dict) and res.get('res_model', False) == 'stock.backorder.confirmation':
            print(res)
            self.action_done()

            partir = data['partir']
            if partir == 'eliminar':
                self.eliminar_partir_albaran()

    @api.multi
    def eliminar_partir_albaran(self):
        self.ensure_one()
        self.cancel_backorder = True
        backorder_pick = self.search([('backorder_id', '=', self.id)])
        backorder_pick.action_cancel()
        self.message_post(body="Pedido en espera <em>%s</em> <b>cancelado</b>." % (
            ",".join([b.name or '' for b in backorder_pick])))

    @api.multi
    def appIncidentar(self, title, message, affected_ids=[]):
        self.ensure_one()
        note = """
        INCIDENCIA APP: %s
        -----------------
        %s
        Afecta a los movimientos de stock con ids:
        %s
        _________________
        """ % (str(title), str(message), str(",".join(map(str, affected_ids))))
        self.addMessageEasy(str(note))
        self.generate_issue()

    @api.multi
    def addMessageEasy(self, note):
        self.ensure_one()
        task = self.task_id
        project = task.project_id
        new_line = ("\n %s" % note)
        project.notes = project.notes + new_line if project.notes else new_line
        task.description = task.description + new_line if task.description else new_line
        self.note = self.note + new_line if self.note else new_line

    @api.multi
    def filterLinesByIDs(self, ids):
        self.ensure_one()
        return self.move_lines.filtered(lambda r: r.id in ids) if isinstance(ids, list) else self.move_lines.filtered(
            lambda r: r.id == int(ids))


    @api.multi
    def getDataTabGeneralInformation(self):
        self.ensure_one()
        task = self.task_id
        project = task.project_id
        sale = project.sale_line_id.order_id if project.sale_line_id and project.sale_line_id.order_id else False
        return {
            "task": {
                "name": task.name,
                "id": task.id
            },
            "project": project.name,
            "picking": self.name,
            "sale": sale.name if sale else "Sin Venta",
            "prefixes": self.env["custody.case.level"].getPosiblePrefixes(),
            "manager": {
                "name": project.user_id.name,
                "phone": project.user_id.partner_id.phone or project.user_id.partner_id.mobile if project.user_id.partner_id else "",
                "email": project.user_id.email
            },
            "commercial": {
                "name": sale.user_id.name,
                "phone": sale.user_id.partner_id.phone or sale.user_id.partner_id.mobile if sale.user_id.partner_id else "",
                "email": sale.user_id.email
            } if sale else {
                "name": "",
                "phone": "",
                "email": ""
            },
            "owner": {
                "name": self.owner_id.name,
                "phone": self.owner_id.phone or self.owner_id.mobile,
                "email": self.owner_id.email,
                "direction": {
                    "street": self.owner_id.street,
                    "street2": self.owner_id.street2,
                    "zip": self.owner_id.zip,
                    "city": self.owner_id.city,
                    "state": self.owner_id.state_id.name if self.owner_id.state_id else "",
                    "country": self.owner_id.country_id.name if self.owner_id.country_id else "",
                }
            },
            "serviceType": project.tipo_servicio,
            "taskType": task.tipo_tarea,
            "pickingType": task.tipo_albaran,
            "priority": self.priority,
            "notes": {
                "projectDescription": project.description,
                "projectNote": project.notes,
                "task": task.description,
                "picking": self.note
            },
            "lines": self.move_lines.getLineDataTab(),
            "specialData": self.getSpecialData()
        }

    @api.multi
    def getModelAFormattedLines(self):
        self.ensure_one()
        names = self.move_lines.mapped("product_id.name")
        res = []
        for name in names:
            res.append({
                "productName": name,
                "amount": int(sum(
                    self.move_lines.filtered(lambda m: m.product_id.name == name).mapped("product_uom_qty")
                ))
            })
        return res

    @api.multi
    def getModelCOrderedLines(self):
        self.ensure_one()
        nonUbicated = self.move_lines.filtered(lambda move: move.dest_location_unknown)

        #nonUbicated_ids = nonUbicated.ids
        #toUbicate_ids = list(set(self.move_lines.ids).difference(nonUbicated_ids))
        #toUbicate = self.move_lines.browse(toUbicate_ids)
        #ubications = toUbicate.mapped("document_move_location_id")

        free_ubications = self.env['stock.location'].getAvailableUbications(self.move_lines.mapped("product_id"), self.company_id, self.task_id.project_id.nave_ids) if nonUbicated else []

        # res = []
        # if nonUbicated:
        #     res.append({
        #         'location': {
        #             "name": "Ubicacion no definida",
        #             "barcode": ""
        #         },
        #         'stockMoves': nonUbicated.getLineDataTab()
        #     })
        # for location in ubications:
        #     res.append({
        #         'location': location.locationDataTab,
        #         'stockMoves': toUbicate.filtered(
        #             lambda move: move.document_move_location_id.id == location.id).getLineDataTab(chorizo=True)
        #     })

        return {
            #'ordered': res,
            'aggregated': self.move_lines.getPosition(),
            'freeUbications': free_ubications,
            'ordered': []
            #'aggregated': self.move_lines.sorted(key=lambda move: move.document_move_location_id.complete_name if move.document_move_location_id else "ZZZZZZZ").getPosition(),
        }

    @api.multi
    def getModelDOrderedLines(self):
        self.ensure_one()
        return self.move_lines.getLineModelD()

    @api.multi
    def getModelEData(self):
        self.ensure_one()
        fullTree = True
        u_reception = self.task_id.project_id.sale_line_id.order_id.unidad_recepcion_id if self.task_id.project_id.sale_line_id and self.task_id.project_id.sale_line_id.order_id else False
        if not u_reception:
            fullTree = False
            u_reception = self.env["custody.case.level"].search([("level", "=", 0)], limit=1)
        return {
            "minimalReceptionUnit": u_reception.parseApp(),
            "tree": self.move_lines.filtered(lambda x: not x.document_id.is_indeterminado).getTreeModelE(fullTree=fullTree)
        }

    @api.multi
    def doIHaveCustodyDocuments(self):
        self.ensure_one()
        document_ids = self.move_lines.mapped("document_id")
        return len(document_ids.ids) > 0

    @api.multi
    def getIfCanEditData(self):
        self.ensure_one()
        if self.task_id.get_model_type() == "F":
            if self.task_id.project_id.archivar_y_recibir:
                return True
            else:
                if self.task_id.tipo_tarea == "archivista":
                    return True
                else:
                    return False
        else:
            return True

    @api.multi
    def getModelFData(self):
        self.ensure_one()
        self.env['ir.sequence'].search([('code', '=', 'product.product')]).mapped('prefix')
        parsed_app_all = self.env["custody.case.level"].sudo().search([]).parseAppMulti()
        return {
            "minUnitArchivado": self.task_id.project_id.unidad_archivado_id.parseApp() if self.getIfCanEditData() else self.move_lines[0].product_id.custody_level_id.parseApp(),
            "canEditData": self.getIfCanEditData(),
            "allChildTypes": parsed_app_all,
            "allProductTypes": parsed_app_all,
            "usedCodes": self.getAllUsedAnonBussinessAndBarcodes(),
            "tree": self.forEach(self.move_lines, lambda move: {
                "type": move.product_id.custody_level_id.parseApp(),
                "anonbussinessCode": move.codigo_identificador or '',
                "barcode": move.etiqueta or '' if not move.document_id else move.codigo_identificador if move.document_id.is_etiqueta_externa else move.etiqueta,
                "documentId": move.document_id.id,
                "stockMoveId": move.id,
                "isTop": True,
                "manual": False,
                "isEtiquetaExterna": False if not move.document_id else move.document_id.is_etiqueta_externa,
                "isBottom": move.product_id.custody_level_id.level == self.task_id.project_id.unidad_archivado_id.level if self.getIfCanEditData() else True,
                "isParentTop": False,
                "productType": move.product_id.custody_level_id.parseApp(),
                "prefix": {
                        "prefix": move.product_id.default_code,
                        "type": move.product_id.custody_level_id.name,
                        "level": move.product_id.custody_level_id.level,
                        "levelId": move.product_id.custody_level_id.id
                    },
                "fatherId": 0,
                "upwardFatherIds": [],
                "wizardId": move.id,
                "archivistaData": {
                    "refClient": "",
                    "dataFilled": False,
                    "year": 0,
                    "description": "",
                    "from": "",
                    "to": "",
                    "destructionDate": 0
                } if not move.document_id else {
                    "refClient": move.document_id.referencia_cliente or "",
                    "dataFilled": False,
                    "year": move.document_id.referencia_cliente or "",
                    "description": move.document_id.descripcion or "",
                    "from": move.document_id.tramo_desde or "",
                    "to": move.document_id.tramo_hasta or "",
                    "destructionDate": move.document_id.getFechaDestruccionYear() or 0
                },
                "origin": "server",
                "onServer": True,
                "childs": []
            })
        }

    @staticmethod
    def forEach(value, function):
        return list(map(function, value))

    @api.multi
    def getSpecialData(self):
        self.ensure_one()
        res = {
            "type": "",
            "A": [],
            "C": {},
            "D": [],
            "E": {},
            "F": ""
        }
        model = self.task_id.get_model_type()
        res["type"] = model
        if model == "A":
            res["A"] = self.getModelAFormattedLines()
        elif model == "C":
            res["C"] = self.getModelCOrderedLines()
        elif model == "D":
            res["D"] = self.getModelDOrderedLines()
        elif model == "E":
            res["E"] = self.getModelEData()
        elif model == "F":
            res["F"] = self.getModelFData()
        return res

