odoo.define('float_percent_field.basic_fields', function (require) {
    "use strict";
    var field_registry = require('web.field_registry');
    var basic_fields = require('web.basic_fields');
    var FieldFloat = basic_fields.FieldFloat;
    var Widget = require('web.Widget');

    /*
     *extending the default float field
     */
    var FieldFloatPercent = FieldFloat.extend({

        // formatType is used to determine which format (and parse) functions

        /**
         * to override to indicate which field types are supported by the widget
         *
         * @type Array<String>
         */
        supportedFieldTypes: ['float'],
    _render: function() {
        this._super.apply(this, arguments);
        if (!this.$el.is("div")){
            this.$el.append($('<span>', {text: "%"}));
        }
    },
    _renderEdit: function() {
        this._super.apply(this, arguments);
        var savedElement = this.$el;
        this.$el = $('<div>', {});
        this.$el.append(savedElement);
        var percentElement = $('<span>', {text: "%"});
        percentElement[0].style.float = "right";
        percentElement[0].style.position = "relative";
        percentElement[0].style.top = "-2em";
        percentElement[0].style.right = "3px";
        this.$el.append(percentElement);
        }
    });

    //registering percent field
    field_registry.add('float_percent', FieldFloatPercent);

    return {
        FieldFloatPercent: FieldFloatPercent
    };
});