# -*- coding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import odoo
from odoo.addons.website.controllers.main import Website
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import Home, ensure_db, Session
import werkzeug
import werkzeug.utils
from odoo.exceptions import AccessError, UserError


class WebsitePortal(Website):
    @http.route(website=True, auth="public")
    def web_login(self, redirect=None, *args, **kw):
        response = super(Website, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            if request.env['res.users'].browse(request.uid).has_group('base.group_user'):
                redirect = b'/web?' + request.httprequest.query_string
            elif request.env['res.users'].browse(request.uid).has_group('anonbussiness_client_portal.group_portal_internal'):
                redirect = b'/web?' + request.httprequest.query_string
            else:
                redirect = '/my'
            return http.redirect_with_hash(redirect)
        return response


class SessionPortal(Session):
    @http.route('/portal/session/destroy', type='json', auth="user")
    def portal_destroy(self):
        request.session.logout()

    @http.route('/portal/logout', type='http', auth="none")
    def portal_logout(self, redirect='/portal/login'):
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)


class HomePortal(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            return werkzeug.utils.redirect('/portal/login', 303)
        if request.env.user and request.env.user.has_group('base.group_public'):
            return http.local_redirect('/portal/login', query=request.params, keep_hash=True)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')

    @http.route('/', type='http', auth="public")
    def index(self, s_action=None, db=None, **kw):
        if request.env.user and request.env.user.has_group('base.group_user'):
            return http.local_redirect('/web', query=request.params, keep_hash=True)
        elif request.env.user and request.env.user.has_group('base.group_portal'):
            return http.local_redirect('/web', query=request.params, keep_hash=True)
        elif request.env.user and request.env.user.has_group('base.group_public'):
            return http.local_redirect('/portal/login', query=request.params, keep_hash=True)

    @http.route('/portal', type='http', auth="none")
    def portal_redirect_login(self, redirect='/portal/login'):
        return werkzeug.utils.redirect(redirect, 303)

    @http.route('/portal/login', type='http', auth="none", sitemap=False)
    def portal_web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            databases = http.db_list()
            values['databases'] = [databases[0]]
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            request.uid = old_uid
            values['error'] = _("Usuario o contraseña incorrectos")
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Error de permisos.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('anonbussiness_client_portal.portal_login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
