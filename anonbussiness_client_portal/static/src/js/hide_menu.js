odoo.define('anonbussiness_client_portal.HideMenu', function (require) {
"use strict";
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var QWeb = core.qweb;
var session = require("web.session");
var ControlPanel = require("web.ControlPanel")

function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); if (enumerableOnly) { symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; }); } keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; if (i % 2) { ownKeys(Object(source), true).forEach(function (key) { _defineProperty(target, key, source[key]); }); } else if (Object.getOwnPropertyDescriptors) { Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)); } else { ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }
    //require the module to modify:
    var WebClient = require("web.WebClient");
ControlPanel.include({
 _render_breadcrumbs: function (breadcrumbs) {
        var self = this;
        breadcrumbs = breadcrumbs.map(function (x) {
          return x.action.action_descr.res_model == "anonbussiness.client.portal" ? _objectSpread(_objectSpread({}, x), {}, {
            title: "Portal del Cliente"
          }) : x;
        });
        return breadcrumbs.map(function (bc, index) {
            return self._render_breadcrumbs_li(bc, index, breadcrumbs.length);
        });
    }
})
    //override the method:
    WebClient.include({
        bind_hashchange: function() {
            var self = this;
            $(window).bind('hashchange', this.on_hashchange);
            var didHashChanged = false;
            $(window).one('hashchange', function () {
                didHashChanged = true;
            });

            var state = $.bbq.getState(true);
            if (_.isEmpty(state) || state.action === "login") {
                self.menu.is_bound.done(function() {
                    self._rpc({
                            model: 'res.users',
                            method: 'read',
                            args: [[session.uid], ['computed_action_id']],
                        })
                        .done(function(result) {
                            if (didHashChanged) {
                                return;
                            }
                            var data = result[0];
                            data.action_id = data.computed_action_id
                            if(data.action_id) {
                                self.action_manager.do_action(data.action_id[0]);
                                self.menu.open_action(data.action_id[0]);
                            } else {
                                var first_menu_id = self.menu.$el.find("a:first").data("menu");
                                if(first_menu_id) {
                                    self.menu.menu_click(first_menu_id);
                                }
                            }
                        });
                });
            } else {
                $(window).trigger('hashchange');
            }
        }
      });
});