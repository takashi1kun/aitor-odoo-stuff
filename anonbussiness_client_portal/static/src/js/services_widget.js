odoo.define('anonbussiness_client_portal.SuggestedServices', function (require) {
"use strict";
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var QWeb = core.qweb;
var session = require("web.session");
var basic_fields = require('web.basic_fields');
var InputField = basic_fields.InputField

var SuggestedServices = AbstractField.extend({
    className: 'o_field_suggested_services',
    supportedFieldTypes: ['one2many','many2many','boolean'],
     events: {
        "click .o_click_add": "_onClickAdd"
    },
    _onClickAdd: function (event) {
        var id = Number.parseInt($(event.target).attr("data"));
        event.preventDefault();
        // alert("Ha seleccionado el servicio con id: "+id)
        var model = 'portal.request';
        var method = 'action_new_from_service';
        var args = {
            service_id: id
        }
        var call_kw = '/web/dataset/call_kw/' + model + '/' + method;
        session.rpc(call_kw, {
            model: model,
            method: method,
            kwargs: args,
            args: []
        }).then(res => this.do_action(res));
        /*var employee_id = parseInt($(event.currentTarget).data('employee-id'));
        return this.do_action({
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
            res_model: 'hr.employee',
            res_id: employee_id,
        });*/
    },
    _render: function () {
        //this.$el.html(QWeb.render('suggestedServicesWidgetTemplate', {renderData: res}))
         var context = _.extend({
            ids: this.value.res_ids,
            model: this.field.relation
         },session.user_context);
         session.rpc('/portal_client/suggested_services', {context: context}).then(
             res => {
                this.$el.html(QWeb.render('suggestedServicesWidgetTemplate', {renderData: res}))
             }
         );
     }
     }
);


fieldRegistry.add('suggested_services', SuggestedServices)
return SuggestedServices;
});
