import werkzeug
import json
from odoo import http
from odoo.http import request


class AppncLogin(http.Controller):
    @http.route('/appnc/amilogged', auth='public')
    def am_i_logged(self):
        return json.dumps({'logged_in': not (request.env.user.id == request.env.ref('base.public_user').id)})

    @http.route('/appnc/logout', auth='user')
    def logout(self):
        return request.session.logout()