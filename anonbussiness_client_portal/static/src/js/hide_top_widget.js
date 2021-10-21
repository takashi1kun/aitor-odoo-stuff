odoo.define('anonbussiness_client_portal.HideTop', function (require) {
"use strict";
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var QWeb = core.qweb;

var HideTop = AbstractField.extend({
    className: 'o_field_hide_top',
    supportedFieldTypes: ['boolean'],
    _render: function () {
         this.$el.html(QWeb.render('hideTopWidgetTemplate'))
     }
     }
);


fieldRegistry.add('hide_top', HideTop);
return HideTop;
});