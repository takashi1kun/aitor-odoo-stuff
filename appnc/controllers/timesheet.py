import ast
from datetime import timedelta, datetime

import werkzeug
import json
from odoo import http, fields
from odoo.http import request
from odoo.addons.app_login_api.models.controller import AppAuth

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class AppncTimesheetController(http.Controller):

    @http.route([
        '/api/test',
    ], type='json', auth="public", csrf=False, cors='*')
    def testCall(self):
        return {
            "lel":"lol"
        }

    # GET METHODS
    @AppAuth
    @http.route([
        '/api/getTasks',
    ], type='json', auth="public", csrf=False, cors='*')
    def getTasks(self):
        TaskModel = request.env['project.task']
        TaskTypeModel = request.env['project.task.type']
        UserModel = request.env['res.users']
        ConfigModel = request.env['ir.config_parameter']
        res = {
            "projects": [],
            "hasStartedPart": False
        }

        allowedTaskStatesString = ConfigModel.sudo().get_param('appnc.taskStatesAllowedInApp')
        allowedTaskStatesIds = TaskTypeModel.search([("id", "in", ast.literal_eval(allowedTaskStatesString))])

        user = UserModel.search([("id", "=", request.uid)])
        allTasksIds = TaskModel.search([
            ("user_id", "=", user.id), # Si la tarea esta asignada a este usuario.
            ("stage_id", "in", allowedTaskStatesIds.ids), # Si la tarea esta en uno de los estados que hemos definido en configuracion para esto.
            ("fecha_inicio", "<", fields.Datetime.now() + timedelta(days=1))  # Solo tareas planeadas para hoy o el pasado, nada de tareas de mañana.
        ])
        allProjectsIds = allTasksIds.mapped("project_id")

        for project in allProjectsIds:
            taskRes = []
            taskIds = allTasksIds.filtered(lambda task: project.id == task.project_id.id)
            for task in taskIds:
                taskRes.append({
                    "name": task.name,
                    "projectName": project.name,
                    "id": task.id,
                    "taskDate": task.fecha_inicio.timestamp()
                })
            taskTimestamps = list(map(lambda x: x["taskDate"], taskRes))
            res["projects"].append({
                "name": project.name,
                "youngestTaskDate": max(taskTimestamps),
                "tasks": taskRes
            })
        if user.AppSetting_hasActiveTask:
            task = user.AppSetting_activeTask_id
            res["hasStartedPart"] = True
            res["startedPart"] = {
                "task": {
                    "name": task.name,
                    "projectName": task.project_id.name,
                    "id": task.id,
                    "taskDate": task.fecha_inicio.timestamp()
                },
                "partId": user.AppSetting_activePart_id.id
            }
        return res

    @AppAuth
    @http.route([
        '/api/task/<int:taskId>',
    ], type='json', auth="public", csrf=False, cors='*')
    def task(self, taskId):
        TaskModel = request.env['project.task']
        UserModel = request.env['res.users']
        PartModel = request.env["appnc.timesheet"]

        user = UserModel.search([("id", "=", request.uid)])
        task = TaskModel.search([("id", "=", taskId)])
        res = {
            "name": task.name,
            "projectName": task.project_id.name,
            "id": taskId,
            "taskDate": task.fecha_inicio.timestamp(),
            "hasStartedPart": user.AppSetting_hasActiveTask and user.AppSetting_activeTask_id.id == task.id,
            "isThereAnyStartedPart": user.AppSetting_hasActiveTask,
            "signedParts": []
         }
        if res["hasStartedPart"]:
            res["openPartId"] = user.AppSetting_activePart_id.id

        partsIds = PartModel.search([
            ("task_id", "=", taskId),
            ("state", "=", "signed")
        ])
        partRes = []
        for part in partsIds:
            date = str(part.date.day)+"/"+str(part.date.month)+"/"+str(part.date.year)
            partDate = datetime.strptime(date+" 00:00:00", "%d/%m/%Y %H:%M:%S")
            today = datetime.strptime(datetime.today().strftime("%d/%m/%Y")+" 00:00:00", "%d/%m/%Y %H:%M:%S")
            partRes.append({
                "name": part.date,
                "partDate": partDate.timestamp(),
                "id": part.id,
                "canBeRectified": (today + timedelta(days=-2)) < partDate,
                "taskName": task.name,
                "taskId": task.id,
                "projectName": task.project_id.name
            })
        res["signedParts"] = partRes
        return res

    @AppAuth
    @http.route([
        '/api/requestRectification',
    ], type='json', auth="public", csrf=False, cors='*')
    def requestRectification(self):
        UserModel = request.env['res.users']
        PartModel = request.env["appnc.timesheet"]
        RectificationModel = request.env["appnc.timesheet.rectification"]
        user = UserModel.search([("id", "=", request.uid)])
        field = self.getFields(request, [
            "id",
            "clientName",
            "clientRank",
            "clientDni",
            "clientEmail",
            "clientSignature"
        ])

        field = dotdict(field)
        part = PartModel.search([("id", "=", field.id)])
        if part.state == "rectificationRequest" or user.AppSetting_hasActiveTask or user.AppSetting_hasActiveRequest:
            return False
        signature = field.clientSignature[22:]
        rectification = RectificationModel.sudo().create({
            "date_requested": fields.Datetime.now(),
            "user_id": user.id,
            "part_id": part.id,
            "clientrep_name": field.clientName,
            "clientrep_position": field.clientRank,
            "clientrep_dni": field.clientDni,
            "clientrep_email": field.clientEmail,
            "clientrep_signature": signature,
            "state": "requested"
        })
        user.AppSetting_hasActiveRequest = True
        part.state = "rectificationRequest"
        rectification.sudo().aprove()
        return True

    @AppAuth
    @http.route([
        '/api/createPart/<int:taskId>',
    ], type='json', auth="public", csrf=False, cors='*')
    def createPart(self, taskId):
        UserModel = request.env['res.users']
        PartModel = request.env["appnc.timesheet"]
        TaskModel = request.env["project.task"]
        user = UserModel.search([("id", "=", request.uid)])
        if user.AppSetting_hasActiveTask or user.AppSetting_hasActiveRequest:
            return False
        task = TaskModel.search([("id", "=", taskId)])
        newPart = PartModel.sudo().create({
            "user_id": user.id,
            "task_id": task.id,
            "partner_id": task.project_id.partner_id.id,
            "state": "progress"
        })
        user.AppSetting_hasActiveTask = True
        user.AppSetting_activeTask_id = task.id
        user.AppSetting_activePart_id = newPart.id
        return {
            "id": newPart.id,
            "clientBussinessName" : newPart.partner_id.name,
            "employeeName" : newPart.user_id.employee_ids[0].name,
            "projectLocationGPS" : newPart.coordinates,
            "allowedHelpers" : task.getHelpers(),
            "allowedProductivityFields" : task.getProductivity(),
            "allowedEquipment" : task.getEquipment()
        }

    @AppAuth
    @http.route([
        '/api/editPart/<int:partId>',
    ], type='json', auth="public", csrf=False, cors='*')
    def editPart(self, partId):
        UserModel = request.env['res.users']
        PartModel = request.env["appnc.timesheet"]
        user = UserModel.search([("id", "=", request.uid)])
        if not user.AppSetting_hasActiveTask:
            return False
        part = PartModel.search([("id", "=", partId)])
        if not part:
            return False
        return {
            "clientBussinessName": part.partner_id.name,
            "employeeName": part.user_id.employee_ids[0].name,
            "taskName": part.task_id.name,
            "projectName": part.task_id.project_id.name,
            "projectLocationGPS": part.coordinates,
            "allowedHelpers": part.getHelpers(),
            "allowedProductivityFields": part.getProductivity(),
            "allowedEquipment": part.getEquipment(),
            "editData": part.getEditData()
        }

    @AppAuth
    @http.route([
        '/api/writeDataPart',
    ], type='json', auth="public", csrf=False, cors='*')
    def writeDataPart(self):
        UserModel = request.env['res.users']
        PartModel = request.env["appnc.timesheet"]
        user = UserModel.search([("id", "=", request.uid)])
        if not user.AppSetting_hasActiveTask:
            return False
        body = self.getFields(request, [
            "field",
            "value",
            "directMode"
        ])
        part = user.AppSetting_activePart_id
        if not part:
            return False
        if not hasattr(part, body.field):
            return False
        forbidenFields = [
            "id",
            "name",
            "user_id",
            "task_id",
            "project_id",
            "partner_id",
            "state",
            "coordinates",
            "company_id",
            "clientrep_name",
            "clientrep_dni",
            "clientrep_position",
            "clientrep_email",
            "signature_surveyor",
            "signature_clientrep",
            "rectification_ids"
        ]
        if body.field in forbidenFields:
            return False
        if body.directMode:
            part[body.field] = body.value
            return True
        elif body.field == "equipment_id":
            EquipmentModel = request.env["appnc.equipment"]
            equipment = EquipmentModel.search([("name", "=", body.value)], limit=1)
            if equipment.id in part.equipment_ids.ids:
                part.equipment_ids = [(3, equipment.id)]
                return True
            else:
                part.equipment_ids = [(4, equipment.id)]
                return True
        elif body.field == "equipment_ids":
            EquipmentModel = request.env["appnc.equipment"]
            equipments = EquipmentModel.search([("name", "in", body.value)])
            part.equipment_ids = [(6,0, equipments.ids)]
            return True

        value = dotdict(body.value)
        if body.field == "helper_line_ids":
            HelperModel = request.env["appnc.timesheet.helper"]
            helper = dotdict(value.helper)
            action = value.action
            if action == "create":
                helperLine = HelperModel.create({
                    "user_id": helper.id,
                    "parent_id": part.id,
                    "time_field": value.hoursField,
                    "time_field_extra": value.hoursExtraField,
                    "time_cabinet_extra": value.hoursGabinet
                })
                return helperLine.id
            elif action == "update":
                helperLine = HelperModel.search([("id", "=", value.id)])
                if not helperLine:
                    return False
                helperLine.time_field = value.hoursField
                helperLine.time_field_extra = value.hoursExtraField
                helperLine.time_cabinet_extra = value.hoursGabinet
                return True
            elif action == "delete":
                helperLine = HelperModel.search([("id", "=", value.id)])
                if not helperLine:
                    return False
                helperLine.unlink()
                return True
            else:
                return False
        elif body.field == "line_ids":
            LineModel = request.env["appnc.timesheet.line"]
            type = dotdict(value.type)
            action = value.action
            if action == "create":
                line = LineModel.create({
                    "parent_id": part.id,
                    "field_id": type.id,
                    "data": value.data
                })
                return line.id
            elif action == "update":
                line = LineModel.search([("id", "=", value.id)])
                if not line:
                    return False
                line.data = value.data
                return True
            elif action == "delete":
                line = LineModel.search([("id", "=", value.id)])
                if not line:
                    return False
                line.unlink()
                return True
            else:
                return False
        else:
            return False
        return True

    @AppAuth
    @http.route([
        '/api/closePart',
    ], type='json', auth="public", csrf=False, cors='*')
    def closePart(self):
        UserModel = request.env['res.users']
        PartModel = request.env["appnc.timesheet"]
        user = UserModel.search([("id", "=", request.uid)])
        if not user.AppSetting_hasActiveTask:
            return False
        body = self.getFields(request, [
            "id",
            "clientName",
            "clientRank",
            "clientDni",
            "clientEmail",
            "clientSignature",
            "employeeSignature"
        ])
        part = PartModel.search([("id", "=", body.id)])
        if not part:
            return False
        if not bool(body.employeeSignature) and not bool(body.clientSignature):
            return False
        part.clientrep_name = body.clientName
        part.clientrep_position = body.clientRank
        part.clientrep_dni = body.clientDni
        part.clientrep_email = body.clientEmail
        part.signature_surveyor = body.employeeSignature
        part.signature_clientrep = body.clientSignature
        part.closePart()
        return True

    # FUNCTIONAL METHODS

    @staticmethod
    def compileFields(objects, fields_names):
        arr = []
        for obj in objects:
            dic = {}
            for field in fields_names:
                dic[field] = obj[field]
            arr.append(dic)
        return arr

    @staticmethod
    def getFields(req, fields_names):
        res = {}
        data = req.jsonrequest["data"]
        for field in fields_names:
            res[field] = data[field]
        return dotdict(res)

    def queryProjectTask(self, user):
        employee = user
        tasks = self.env["project.task"].sudo().search([
            ("user_id", "=", user.id)
        ])

    def queryTasks(self, user):
        tasks = self.env["project.task"].sudo().search([
            ("user_id", "=", user.id)
        ])
        project_ids = []
        for task in tasks:
            project_ids.append(task.project_ids.id)
        projects = self.env["project.project"].sudo().search[
            ("id", "in", project_ids)
        ]
        return self.compileFields(
            projects,
            ["id", "name", "state"]
        )

    def queryProductivityFields(self):
        prodFields = self.env["appnc.productivity"].sudo().search([
            ("active", "=", True)
        ])
        return self.compileFields(
            prodFields,
            ["name", "type"]
        )

    def queryTimesheets(self, task_id, user_id):
        timesheets = self.env["appnc.timesheet"].sudo().search([
            ("employee_id", "=", user_id),
            ("task_id", "=", task_id),
            ("state", "in", ["new","progress","signed"])
        ])
        return self.compileFields(
            timesheets,
            ["id", "date", "state", "time_field"]
        )
