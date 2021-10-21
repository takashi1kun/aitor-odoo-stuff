# -*- coding: utf-8 -*-
# (c) 2020 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import functools
import json
import logging
import random
import os
import werkzeug

logger = logging.getLogger(__name__)

from odoo import models, fields, api, http, exceptions
from odoo.http import Controller, request, route


def check_user(f):
    @functools.wraps(f)
    def wrap(self, *args, **kw):
        device_id = request.jsonrequest['deviceid']
        device = http.request.env['anonbussiness.app.model.login'].sudo().search(
            [('device_code', '=', device_id)], limit=1)
        if not device:
            body = json.dumps({"body": ["Session Expired"]})
            return werkzeug.wrappers.Response(body, status=403, headers=[
                ('Content-Type', 'application/json'), ('Content-Length', len(body))
            ])
        if not device.is_logged_in:
            body = json.dumps({"body": ["Session Expired"]})
            return werkzeug.wrappers.Response(body, status=403, headers=[
                ('Content-Type', 'application/json'), ('Content-Length', len(body))
            ])
        request.uid = device.last_logged_user.id
        if not request.uid:
            body = json.dumps({"body": ["Session Expired"]})
            return werkzeug.wrappers.Response(body, status=403, headers=[
                ('Content-Type', 'application/json'), ('Content-Length', len(body))
            ])

        device.logindevice()
        return f(self, *args, **kw)

    return wrap


class AnonBussinessAppApiTasksMenu(Controller):

    def getDeviceCode(self, req):
        device_id = req.jsonrequest['deviceid']
        return req.env['anonbussiness.app.model.login'].sudo().search(
            [('device_code', '=', device_id)], limit=1)

    @check_user
    @http.route([
        '/apiappanonbussiness/getuserdata',
    ], type='json', auth="public", csrf=False, cors='*')
    def getUserData(self, *args, **kw):
        user = request.env.user
        return {
            "name": user.name,
            "avatar": user.image_small or user.image_medium or user.image or self.placeholder or ''
        }

    @property
    def placeholder(self):
        image = 'placeholder.png'
        web = http.addons_manifest.get('web', False)
        if web:
            addons_path = web.get('addons_path', False)
            if addons_path:
                return base64.b64encode(open(os.path.join(addons_path, 'web', 'static', 'src', 'img', image), 'rb').read()).decode('utf-8')
        return ""

    @check_user
    @http.route([
        '/apiappanonbussiness/getnotifications/<int:section>',
    ], type='json', auth="public", csrf=False, cors='*')
    def getNotifications(self,section, *args, **kw):
        user = request.env.user
        res = request.env["anonbussiness.app.notification"].getUserNotifications(
            user=user,
            query_number=section
        )
        return res

    @check_user
    @http.route([
        '/apiappanonbussiness/task/incidence/<int:task_id>',
    ], type='json', auth="public", csrf=False, cors='*')
    def incidentTask(self, task_id, *args, **kw):
        user = request.env.user
        task = request.env["project.task"].sudo().search([("id", "=", task_id)], limit=1)
        device = self.getDeviceCode(request)
        gps = request.jsonrequest['gps']
        has_gps = bool(gps)
        log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
            "device_id": device.id,
            "user_id": user.id,
            "type": "incidence_task",
            "is_task_related": True,
            "has_gps_location": has_gps,
            "related_task_id": task.id
        })
        if has_gps:
            gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
            log_id.gps_location_id = gps_id.id
        task.albaran_id.appIncidentar("INCIDENCIA MANUAL", request.jsonrequest['data'])
        return True

    @check_user
    @http.route([
        '/apiappanonbussiness/task/all',
    ], type='json', auth="public", csrf=False, cors='*')
    def getAllTaskDataPartial(self, *args, **kw):
        tasks = request.env["project.task"].getTasksByUser()
        return tasks.getTaskMinData()

    @check_user
    @http.route([
        '/apiappanonbussiness/task/id/<int:task_id>',
    ], type='json', auth="public", csrf=False, cors='*')
    def getTaskDataComplete(self, task_id, *args, **kw):
        task = request.env["project.task"].sudo().search([("id", "=", task_id)], limit=1)
        device = self.getDeviceCode(request)
        user = request.env.user
        gps = request.jsonrequest['gps']
        has_gps = bool(gps)
        log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
            "device_id": device.id,
            "user_id": user.id,
            "type": "open_task",
            "is_task_related": True,
            "has_gps_location": has_gps,
            "related_task_id": task.id
        })
        if has_gps:
            gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
            log_id.gps_location_id = gps_id.id
        return task.getFullDataAPP()

    # TODO: Implementar, esta no esta implementada
    @check_user
    @http.route([
        '/apiappanonbussiness/task/save/id/<int:task_id>',
    ], type='json', auth="public", csrf=False, cors='*')
    def saveTaskDataOnline(self, task_id, *args, **kw):
        task = request.env["project.task"].sudo().search([("id", "=", task_id)], limit=1)
        request.jsonrequest['data']
        return False

    @check_user
    @http.route([
        '/apiappanonbussiness/task/complete/id/<int:task_id>',
    ], type='json', auth="public", csrf=False, cors='*')
    def completeTask(self, task_id, *args, **kw):
        task = request.env["project.task"].sudo().search([("id", "=", task_id)], limit=1)
        # interface FinishTaskData {
        #   model: ModelLetters;
        #   modelBSavedData: MiniStockMove[];
        #   modelCSavedData: StockMoveState[];
        #   modelDSavedData: StockMoveExtractionState[];
        #   modelESavedData: StockMoveTreeNode[];
        #   modelFSavedData:  ModelFTreeNode[];
        # }
        taskData = request.jsonrequest['data']
        modelLetter = taskData['model']
        # 2020/12/31
        # Sobreescribimos el lenguage para evitar errores del tipo
        # psycopg2.IntegrityError: insert or update on table "ir_translation" violates foreign key constraint "ir_translation_lang_fkey_res_lang"
        # DETAIL: Key (lang)=(es_419) is not present in table "res_lang"
        ctx = dict(task.env.context)
        ctx.update({'lang': 'es_ES'})
        task = task.with_context(ctx)
        if taskData['message']:
            note = ''' \n    
_______________________________ \n  
NOTA DE LA APP: \n  
%s \n  
_______________________________ \n  
            ''' % taskData['message']
            task.description = note.replace("\n", "<br>") if not bool(task.description) else task.description + note.replace("\n", "<br>")
            task.albaran_id.note = note if not bool(task.albaran_id.note) else task.albaran_id.note + note
            task.albaran_id.message_post(
                subject="NOTA DE LA APP",
                body=note.replace("\n", "<br>"),
                message_type="comment"
            )
            task.message_post(
                subject="NOTA DE LA APP",
                body=note.replace("\n", "<br>"),
                message_type="comment"
            )
        if modelLetter == "A":
            task.albaran_id.handleAppTaskFinishA()
        elif modelLetter == "B":
            task.albaran_id.handleAppTaskFinishB(taskData["modelBSavedData"])
        elif modelLetter == "C":
            task.albaran_id.handleAppTaskFinishC(taskData["modelCSavedData"])
        elif modelLetter == "D":
            task.albaran_id.handleAppTaskFinishD(taskData["modelDSavedData"])
        elif modelLetter == "E":
            task.albaran_id.handleAppTaskFinishE(taskData["modelESavedData"])
        elif modelLetter == "F":
            task.albaran_id.handleAppTaskFinishF(taskData["modelFSavedData"])
        else:
            raise Exception("Error de letra")

        device = self.getDeviceCode(request)
        user = request.env.user
        gps = request.jsonrequest['gps']
        has_gps = bool(gps)
        log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
            "device_id": device.id,
            "user_id": user.id,
            "type": "end_task",
            "is_task_related": True,
            "has_gps_location": has_gps,
            "related_task_id": task.id
        })
        if has_gps:
            gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
            log_id.gps_location_id = gps_id.id
        return True


class AnonBussinessAppApiLogin(Controller):
    @check_user
    @http.route([
        '/apiappanonbussiness/logout',
    ], type='json', auth="public", csrf=False, cors='*')
    def logout(self, *args, **kw):
        device = self.getDeviceCode(request)
        user = request.env.user
        gps = request.jsonrequest['gps']
        has_gps = bool(gps)
        log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
            "device_id": device.id,
            "user_id": user.id,
            "type": "logout",
            "is_conection_related": True,
            "has_gps_location": has_gps
        })
        if has_gps:
            gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
            log_id.gps_location_id = gps_id.id
        device.logoff()
        return {'logoff': True}

    # Esta es para la prueba manual del usuario, para que el pueda ver si las tiene activas recibiendo una que pueda ver
    @check_user
    @http.route([
        '/apiappanonbussiness/testnotification',
    ], type='json', auth="public", csrf=False, cors='*')
    def testNotification(self, *args, **kw):
        device = self.getDeviceCode(request)
        device.sendNotification("Notificacion de Prueba", "Probando sistema de notificaciones")
        return True

    # Esta es para una prueba automatica que se hace por detras y no se debe ver que hace el sistema para saber si funcionan las notificaciones
    @check_user
    @http.route([
        '/apiappanonbussiness/checkifnotificationsenabled',
    ], type='json', auth="public", csrf=False, cors='*')
    def testNotificationRegistered(self, *args, **kw):
        device = self.getDeviceCode(request)
        device.sendNotificationTest()
        return True

    @http.route([
        '/apiappanonbussiness/login',
    ], type='json', auth="public", csrf=False, cors='*')
    def login(self):
        device = self.getDeviceCode(request)
        data = request.jsonrequest['data']
        gps = request.jsonrequest['gps']
        has_gps = bool(gps)
        if self.checkUserPassword(request):
            user = request.env['res.users'].sudo().search([('login', '=', data['user'])])
            device_id = self.generateUniqueId(request)
            if device:
                device.device_code = device_id
                device.last_logged_user = user.id
                if user.id not in device.users_ids.ids:
                    device.users_ids = [(4, user.id)]
                device.is_logged_in = True
                device.loginuser()
                log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
                    "device_id": device.id,
                    "user_id": user.id,
                    "type": "login",
                    "is_conection_related": True,
                    "has_gps_location": has_gps
                })
                if has_gps:
                    gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
                    log_id.gps_location_id = gps_id.id
                request.uid = user.id
            else:
                new_device = request.env['anonbussiness.app.model.login'].sudo().create({
                    'device_code': device_id,
                    'last_logged_user': user.id,
                    'users_ids': [(6, 0, [user.id])],
                    'is_logged_in': True
                })
                new_device.loginuser()
                log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
                    "device_id": new_device.id,
                    "user_id": user.id,
                    "type": "first_login",
                    "is_conection_related": True,
                    "has_gps_location": has_gps
                })
                if has_gps:
                    gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
                    log_id.gps_location_id = gps_id.id
                request.uid = user.id
            return {'login': 'succesful', 'deviceid': device_id}
        else:
            return {'login': 'fail', 'deviceid': ""}

    @http.route([
        '/apiappanonbussiness/registerNotifications',
    ], type='json', auth="public", csrf=False, cors='*')
    def registerNotifications(self):
        device = self.getDeviceCode(request)
        if device:
            if (not (device.user_notification_key == request.jsonrequest['data'])) or not device.can_send_notifications:
                request.env["anonbussiness.app.model.login.log"].sudo().create({
                    "device_id": device.id,
                    "user_id": device.last_logged_user.id,
                    "type": "notification_registered",
                    "has_gps_location": False
                })
            device.user_notification_key = request.jsonrequest['data']
            device.can_send_notifications = True
            return True
        else:
            return False

    @http.route([
        '/apiappanonbussiness/identificated',
    ], type='json', auth="public", csrf=False, cors='*')
    def checkDeviceCode(self):
        device = self.getDeviceCode(request)
        if not device:
            return False
        elif device.is_logged_in:
            gps = request.jsonrequest['gps']
            has_gps = bool(gps)
            log_id = request.env["anonbussiness.app.model.login.log"].sudo().create({
                "device_id": device.id,
                "user_id": device.last_logged_user.id,
                "type": "conection",
                "is_conection_related": True,
                "has_gps_location": has_gps
            })
            if has_gps:
                gps_id = request.env["anonbussiness.app.model.login.log.gps"].createGPS(gps, log_id)
                log_id.gps_location_id = gps_id.id
            return True
        else:
            return False
    keylist = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','0','1','2','3','4','5','6','7','8','9']
    def generateUniqueId(self, req):
        model = req.env['anonbussiness.app.model.login'].sudo()
        keyList = self.keylist
        key = ''.join(map(lambda x: keyList[random.randint(0, 61)],range(32)))
        # key = secrets.token_hex(32)
        return key if not model.search([('device_code', '=', key)], limit=1) else self.generateUniqueId(req)

    def getDeviceCode(self, req):
        device_id = req.jsonrequest['deviceid']
        return req.env['anonbussiness.app.model.login'].sudo().search(
            [('device_code', '=', device_id)], limit=1)

    def checkUserPassword(self, req):
        data = req.jsonrequest['data']
        users = req.env['res.users']
        user = users.sudo().search([('login', '=', data['user'])], limit=1)
        password = data['pass']
        res = False
        try:
            user.sudo(user).check_credentials(password)
            res = True
        except exceptions.AccessDenied:
            res = False
        finally:
            return res
        # return True if users.sudo().search([('login', '=', user),('password_crypt', '=', password)]) else False

