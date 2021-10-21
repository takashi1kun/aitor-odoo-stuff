odoo.define('web_search_disable_add_custom_filter', function (require) {
'use strict';
var FilterMenu = require('web.FilterMenu');
var GroupByMenu = require('web.GroupByMenu');
var FavoriteMenu = require('web.FavoriteMenu');
var Sidebar = require('web.Sidebar');

function no_edit_check(element){
    if (element.searchview){
            if (element.searchview.fields_view){
                if (element.searchview.fields_view.arch){
                    if (element.searchview.fields_view.arch.attrs){
                        if (element.searchview.fields_view.arch.attrs.string){
                            if (element.searchview.fields_view.arch.attrs.string.indexOf('no_edit') !== -1) {
                                return true;
                            }
                        }
                    }
                }
            }
        }
        return false;
}

function megaCheck(element){
    if (element.__parentedParent){
        if (element.__parentedParent.__parentedChildren){
            var view = element.__parentedParent.__parentedChildren.find(x => x.arch != undefined);
            if (view){
                if (view.arch){
                    if (view.arch.attrs){
                        if (view.arch.attrs.class){
                        return view;
                        }
                    }
                }
            }
        }
    }
    return false;
}
var ListRenderer = require('web.ListRenderer');
ListRenderer.include({
    init: function (parent, state, params) {
        this._super(parent, state, params);
        if (params.arch){
            if (params.arch.attrs){
                if (params.arch.attrs.class){
                    if (params.arch.attrs.class.indexOf('no_print') !== -1 && params.arch.attrs.class.indexOf('no_action') !== -1){
                        state.hasSelectors = false;
                        this.hasSelectors = false;
                    }
                }
            }
        }
    },
});

Sidebar.include({
    start: function () {
        this._super();
        var check = megaCheck(this);
        if (check != false){
            if(check.arch.attrs.class.indexOf('no_print') !== -1){
                for (var i =0; i < this.sections.length; i++){
                   if (this.sections[i].name && this.sections[i].name === "print") {
                      this.sections.splice(i,1);
                      break;
                   }
                }
                if (this.items && this.items.print){
                    this.items.print = [];
                }
            }
            if(check.arch.attrs.class.indexOf('no_action') !== -1){
                for (var i =0; i < this.sections.length; i++){
                   if (this.sections[i].name && this.sections[i].name === "other") {
                      this.sections.splice(i,1);
                      break;
                   }
                }
                if (this.items && this.items.other){
                    this.items.other = [];
                }
            }
            // this.$('.divider:last').hide();

            this._redraw();
        }
    }
});

GroupByMenu.include({
    start: function () {
        this._super();
        if (no_edit_check(this)){
            this.$('.divider:last').hide();
            this.$add_group.hide();
        }
    }
});
FilterMenu.include({
    start: function () {
        this._super();
        if (no_edit_check(this)){
            this.$('.divider:last').hide();
            this.$add_filter.hide();
        }
    }
});
FavoriteMenu.include({
    start: function () {
        this._super();
        this.$button_dropdown = this.$('button.o_dropdown_toggler_btn');
        if (no_edit_check(this)){
            this.$('.divider:last').hide();
            this.$save_search.hide();
            this.$button_dropdown.hide();
        }
    }
});

});