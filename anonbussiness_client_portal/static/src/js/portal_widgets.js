odoo.define('anonbussiness_client_portal.PortalList', function (require) {
"use strict";
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var QWeb = core.qweb;
var session = require("web.session");
var relational_fields = require('web.relational_fields');
var FieldMany2ManyTags = relational_fields.FieldMany2ManyTags;
var basic_fields = require('web.basic_fields');
var mixins_get = require('web.mixins')
var Events = mixins_get.EventDispatcherMixin
var InputField = basic_fields.InputField
var FieldMany2One = relational_fields.FieldMany2One
var rpc = require('web.rpc');
var pyeval = require('web.pyeval');
var FormRenderer = require('web.FormRenderer');
var FieldMany2Many = relational_fields.FieldMany2Many;
var FieldStatus = relational_fields.FieldStatus;
var ListRenderer = require('web.ListRenderer');
var qweb = QWeb;
FormRenderer.include({
/**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagLabel: function (node) {
        var self = this;
        var text;
        var fieldName = node.tag === 'label' ? node.attrs.for : node.attrs.name;
        if ('string' in node.attrs) { // allow empty string
            text = node.attrs.string;
        } else if (fieldName && fieldName in this.state.fields) {
            text = this.state.fields[fieldName].string;
        } else  {
            return this._renderGenericTag(node);
        }
        var $result = $('<label>', {
            class: 'o_form_label',
            for: this._getIDForLabel(fieldName),
            text: text,
        });
        if (node.tag === 'label') {
            this._handleAttributes($result, node);
        }
        var modifiersOptions;
        if (fieldName) {
            modifiersOptions = {
                callback: function (element, modifiers, record) {
                    var widgets = self.allFieldWidgets[record.id];
                    var widget = _.findWhere(widgets, {name: fieldName});
                    if (!widget) {
                        return; // FIXME this occurs if the widget is created
                                // after the label (explicit <label/> tag in the
                                // arch), so this won't work on first rendering
                                // only on reevaluation
                    }
                    element.$el.toggleClass('o_form_label_empty', !!( // FIXME condition is evaluated twice (label AND widget...)
                        record.data.id
                        && (modifiers.readonly || self.mode === 'readonly')
                        && !widget.isSet()
                    ));
                },
            };
        }
        // FIXME if the function is called with a <label/> node, the registered
        // modifiers will be those on this node. Maybe the desired behavior
        // would be to merge them with associated field node if any... note:
        // this worked in 10.0 for "o_form_label_empty" reevaluation but not for
        // "o_invisible_modifier" reevaluation on labels...
        this._registerModifiers(node, this.state, $result, modifiersOptions);
        return $result;
    },
})

var FieldMany2ManyTreeUnlink = FieldMany2Many.extend({
    className: 'o_field_many2many_tree_unlink',
    supportedFieldTypes: ['many2many'],
    _render: function () {
        if (!this.view) {
            return this._super();
        }
        if (this.renderer) {
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            this.renderer.updateState(this.value, {'columnInvisibleFields': this.currentColInvisibleFields});
            this.pager.updateState({ size: this.value.count });
            return $.when();
        }
        var arch = this.view.arch;
        var viewType;
        if (arch.tag === 'tree') {
            viewType = 'list';
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            this.renderer = new ListRenderer(this, this.value, {
                arch: arch,
                editable: this.mode === 'edit' && arch.attrs.editable,
                addCreateLine: !this.isReadonly && this.activeActions.create,
                addTrashIcon: !this.isReadonly,
                viewType: viewType,
                columnInvisibleFields: this.currentColInvisibleFields,
            });
        }
        this.$el.addClass('o_field_x2many o_field_x2many_' + viewType);
        return this.renderer ? this.renderer.appendTo(this.$el) : this._super();
    },
    _onDeleteRecord: function (ev) {
        ev.stopPropagation();
        var operation = 'FORGET';
        this._setValue({
            operation: operation,
            ids: [ev.data.id],
        });
    },
})


var FieldStatusOrdered = AbstractField.extend({
    className: 'o_statusbar_status',
    events: {
        'click button:not(.dropdown-toggle)': '_onClickStage',
    },
    specialData: "_fetchSpecialStatus",
    supportedFieldTypes: ['selection', 'many2one'],
    /**
     * @override init from AbstractField
     */
    init: function () {
        this._super.apply(this, arguments);
        this._setState();
        this._onClickStage = _.debounce(this._onClickStage, 300, true); // TODO maybe not useful anymore ?
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override _reset from AbstractField
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this._setState();
    },
    _setState: function () {
        var self = this;
        if (this.field.type === 'many2one') {
            this.status_information = _.map(this.record.specialData[this.name], function (info) {
                return _.extend({
                    selected: info.id === self.value.res_id,
                }, info);
            });
        } else {
            var selection = this.field.selection;
            if (this.attrs.statusbar_visible) {
                var restriction = this.attrs.statusbar_visible.split(",");
                selection = _.filter(selection, function (val) {
                    return _.contains(restriction, val[0]) || val[0] === self.value;
                });
            }
            if (this.attrs.statusbar_visible) {
                var order = this.attrs.statusbar_visible.split(",");
                var newselection = order.map(element => selection.find(el2 => el2[0] == element)).filter(n => n) || []
                var remainingSelection = selection.find(el => !order.includes(el[0])) || [];
                if (remainingSelection.length > 0) {remainingSelection.forEach(x => newselection.push(x))};
                selection = newselection;
            }
            this.status_information = _.map(selection, function (val) {
                return { id: val[0], display_name: val[1], selected: val[0] === self.value, fold: false };
            });
        }
    },
    /**
     * @override _render from AbstractField
     * @private
     */
    _render: function () {
        var selections = _.partition(this.status_information, function (info) {
            return (info.selected || !info.fold);
        });
        this.$el.html(qweb.render("FieldStatus.content", {
            selection_unfolded: selections[0],
            selection_folded: selections[1],
            clickable: !!this.attrs.clickable,
        }));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when on status stage is clicked -> sets the field value.
     *
     * @private
     * @param {MouseEvent} e
     */
    _onClickStage: function (e) {
        this._setValue($(e.currentTarget).data("value"));
    }
});


var InternalUrlWidget = InputField.extend({
    className: 'o_field_internalurl',
    events: _.extend({}, InputField.prototype.events, {
        'click': '_onClick',
    }),
    supportedFieldTypes: ['char'],

    /**
     * Urls are links in readonly mode.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'a' : 'input';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the associated link.
     *
     * @override
     */
    getFocusableElement: function () {
        return this.mode === 'readonly' ? this.$el : this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * In readonly, the widget needs to be a link with proper href and proper
     * support for the design, which is achieved by the added classes.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this.attrs.text || this.value)
            .addClass('o_form_uri o_text_overflow')
            .attr('href', this.value);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Prevent the URL click from opening the record (when used on a list).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick: function (ev) {
        ev.stopPropagation();
    },
});

var PortalList = AbstractField.extend({
    className: 'o_field_portal_list',
    supportedFieldTypes: ['one2many','many2many'],
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    init: function () {
        this._super.apply(this, arguments);
    },
    fieldsToFetch: {
        name: {type: 'char'},
    },
    activate: function () {
        return this.many2one ? this.many2one.activate() : false;
    },
    isSet: function () {
        return !!this.value && this.value.count;
    },
    reset: function (record, event) {
        this._super.apply(this, arguments);
        if (event && event.target === this) {
            this.activate();
        }
    },
    _addTag: function (data) {
        if (!_.contains(this.value.res_ids, data.id)) {
            this._setValue({
                operation: 'ADD_M2M',
                ids: data
            });
        }
    },
    _onFieldChanged: function (ev) {
        if (ev.target !== this.many2one) {
            return;
        }
        ev.stopPropagation();
        var newValue = ev.data.changes[this.name];
        if (newValue) {
            this._addTag(newValue);
            this.many2one.reinitialize(false);
        }
    },
    _render: function () {
         var context = _.extend({
            ids: this.value.res_ids,
            model: this.field.relation
         },session.user_context);
         session.rpc('/portal_client/render_list', {context: context}).then(
             res => {
                this.$el.html(QWeb.render('portalListWidgetTemplate', {renderData: res}))
             }
         );
     }
     }
);
var AddressWidget = FieldMany2One.extend({
    className: 'o_field_address_widget',
    supportedFieldTypes: ['many2one'],
    _rpc: function (params, options) {
        var query = rpc.buildQuery(params);
        //var def = this.call('ajax', 'rpc', query.route, query.params, options);
        //return def ? def.promise() : $.Deferred().promise();
        return session.rpc(query.route, query.params)
    },
    _renderReadonly: function () {
        this._rpc({
                        model: this.field.relation,
                        method: 'read',
                        args: [[this.value.data.id], ["computed_address_name"]],
                        context: _.extend({}, this.record.getContext(), {bin_size: true})
                    }).then(result => {
                        this.$el.text(result[0].computed_address_name)
                    })

    },
})
fieldRegistry.add('portal_list', PortalList).add('address_widget', AddressWidget).add('internal_url_widget', InternalUrlWidget).add('m2m_tree_unlink',FieldMany2ManyTreeUnlink).add('statusbar_ordered',FieldStatusOrdered);
return PortalList;
});