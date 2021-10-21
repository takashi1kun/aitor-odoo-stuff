odoo.define('anonbussiness_client_portal.CsvTable', function (require) {
"use strict";
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var QWeb = core.qweb;
var session = require("web.session");
var basic_fields = require('web.basic_fields');
var InputField = basic_fields.InputField

var CsvTable2 = AbstractField.extend({
    className: "o_field_csv_table",
    supportedFieldTypes: ['binary'],
    csv_headers: [],
  csv_rows: [],
  csv_page: 1,
  rows_per_page: 5,
  no_csv: false,
  csv_table_html_elements: {
    parent: undefined,
    main: undefined,
    table: undefined,
    thead: undefined,
    tbody: undefined,
    header_tr: undefined,
    navigation: undefined,
    button_prev: undefined,
    button_next: undefined,
    pager: undefined,
    pager_input_current: undefined,
    pager_input_max: undefined
  },
  csv_paginate: function (array, page_size, page_number) {
    return array.slice((page_number - 1) * page_size, page_number * page_size);
  },
  get_current_page_rows: function () {
    return this.csv_paginate(this.csv_rows, this.rows_per_page, this.csv_page);
  },
  get_number_of_pages: function () {
    return Math.ceil(this.csv_rows.length / this.rows_per_page);
  },
  initialize_csv: function (csv_string) {
    let rows = csv_string.split("\n");
    if (rows.length) {
      rows = rows[rows.length - 1] == "" ? rows.slice(0, -1) : rows;
    }
    //csv_table_html_elements;
    this.csv_table_html_elements.parent = this.$el.get(0);
    this.csv_table_html_elements.main = document.createElement("main");
    this.csv_table_html_elements.navigation = document.createElement("nav");
    this.csv_table_html_elements.table = document.createElement("table");
    this.csv_table_html_elements.thead = document.createElement("thead");
    this.csv_table_html_elements.tbody = document.createElement("tbody");
    this.csv_table_html_elements.header_tr = document.createElement("tr");
    this.csv_table_html_elements.button_prev = document.createElement("button");
    this.csv_table_html_elements.button_prev.innerText = "<";
    this.csv_table_html_elements.button_next = document.createElement("button");
    this.csv_table_html_elements.button_next.innerText = ">";
    this.csv_table_html_elements.pager = document.createElement("div");
    this.csv_table_html_elements.pager_input_current = document.createElement(
      "input"
    );
    this.csv_table_html_elements.pager_input_max = document.createElement(
      "input"
    );
    this.csv_table_html_elements.pager_input_current.style.width = "40px";
    this.csv_table_html_elements.pager_input_max.style.width = "40px";
    this.csv_table_html_elements.pager_input_current.type = "number";
    this.csv_table_html_elements.pager_input_max.type = "number";
    this.csv_table_html_elements.pager.style.display = "inline";
    this.csv_table_html_elements.pager_input_max.style.display = "inline";
    this.csv_table_html_elements.pager_input_current.style.display = "inline";
    this.csv_table_html_elements.pager_input_max.disabled = true;
    this.csv_table_html_elements.pager_input_current.min = 1;
    const firstLabel = document.createElement("span");
    firstLabel.innerText = "Pagina ";
    this.csv_table_html_elements.pager.appendChild(firstLabel);
    this.csv_table_html_elements.pager.appendChild(
      this.csv_table_html_elements.pager_input_current
    );
    const secondLabel = document.createElement("span");
    secondLabel.innerText = " de ";
    this.csv_table_html_elements.pager.appendChild(secondLabel);
    this.csv_table_html_elements.pager.appendChild(
      this.csv_table_html_elements.pager_input_max
    );

    this.csv_table_html_elements.main.appendChild(
      this.csv_table_html_elements.table
    );

    this.csv_table_html_elements.navigation.appendChild(
      this.csv_table_html_elements.button_prev
    );
    this.csv_table_html_elements.navigation.appendChild(
      this.csv_table_html_elements.pager
    );
    this.csv_table_html_elements.navigation.appendChild(
      this.csv_table_html_elements.button_next
    );
    this.csv_table_html_elements.main.appendChild(
      this.csv_table_html_elements.navigation
    );
    this.csv_table_html_elements.table.appendChild(
      this.csv_table_html_elements.thead
    );
    this.csv_table_html_elements.table.appendChild(
      this.csv_table_html_elements.tbody
    );
    this.csv_table_html_elements.thead.appendChild(
      this.csv_table_html_elements.header_tr
    );
    this.csv_table_html_elements.button_next.addEventListener("click", () =>
      this.renderNextPage()
    );
    this.csv_table_html_elements.button_prev.addEventListener("click", () =>
      this.renderPrevPage()
    );
    this.csv_table_html_elements.pager_input_current.addEventListener(
      "blur",
      () => this.changePageInput()
    );
    this.csv_table_html_elements.pager_input_current.addEventListener(
      "change",
      () => this.changePageInput()
    );
    switch (rows.length) {
      case 0: {
        this.csv_headers = [];
        this.csv_rows = [];
        this.no_csv = true;
        break;
      }
      case 1: {
        this.csv_headers = rows[0].split(",");
        this.csv_rows = [];
        break;
      }
      default: {
        this.csv_headers = rows[0].split(",");
        this.csv_rows = rows.slice(1).map((x) => x.split(","));
        break;
      }
    }
  },
  table_first_render: function () {
    if (this.csv_page > 1) {
      return;
    }
    const num_pages = this.get_number_of_pages();
    this.csv_table_html_elements.pager_input_max.value = num_pages;
    this.csv_table_html_elements.pager_input_current.value = 1;
    this.csv_table_html_elements.pager_input_current.max = num_pages;
    this.csv_table_html_elements.table.className =
      "o_list_view table table-condensed table-hover table-striped o_list_view_ungrouped";
    this.csv_table_html_elements.header_tr.innerHTML = this.csv_headers
      .map((x) => this.header(x))
      .join("\n");
    this.csv_table_html_elements.tbody.innerHTML = this.renderPage(
      this.get_current_page_rows()
    );
    //this.csv_table_html_elements.navigation;
    this.csv_table_html_elements.parent.innerHTML = ``;
    this.renderNavigation();
    this.csv_table_html_elements.parent.appendChild(
      this.csv_table_html_elements.main
    );
  },
  renderNavigation: function () {
    if (this.get_number_of_pages() == 1) {
      this.csv_table_html_elements.navigation.hidden = true;
    }
    this.csv_table_html_elements.button_prev.disabled = this.csv_page <= 1;
    this.csv_table_html_elements.button_next.disabled =
      this.get_number_of_pages() <= this.csv_page;
    this.csv_table_html_elements.pager_input_current.value = this.csv_page;
  },
  renderNextPage: function () {
    this.csv_page = this.csv_page + 1;
    this.renderPageNow();
  },
  renderPrevPage: function () {
    this.csv_page = this.csv_page - 1;
    this.renderPageNow();
  },
  changePageInput: function () {
    const tentativeValue = Math.max(
      1,
      Math.min(
        this.get_number_of_pages(),
        this.csv_table_html_elements.pager_input_current.value
      )
    );
    if (
      tentativeValue != this.csv_table_html_elements.pager_input_current.value
    ) {
      this.csv_table_html_elements.pager_input_current.value = tentativeValue;
    }
    this.csv_page = tentativeValue;
    this.renderPageNow();
  },
  renderPageNow: function () {
    this.renderNavigation();
    this.csv_table_html_elements.tbody.innerHTML = this.renderPage(
      this.get_current_page_rows()
    );
  },
  renderPage: function (rows) {
    if (
      this.csv_page != 1 &&
      this.csv_page == this.get_number_of_pages() &&
      rows.length < this.rows_per_page
    ) {
      for (var i = rows.length; i < this.rows_per_page; i++) {
        rows.push(Array.apply(null, Array(rows[0].length)).map(() => "-"));
      }
    }
    return rows.map((x) => this.tbody(x)).join("\n");
  },
  header: function (element) {
    return `<th>${element}</th>`;
  },
  tbody: function (row) {
    return `<tr>${row.map((x) => this.line(x)).join("\n")}</tr>`;
  },
  line: function (element) {
    return `<td>${element}</td>`;
  },
  generateHtmlTable: function (csvBloat, rows_per_page = 5) {
    this.rows_per_page = rows_per_page;
    const csv = window.atob(csvBloat);
    this.initialize_csv(csv);
    if (!this.no_csv) {
      this.table_first_render();
    }
  },
  _render: function () {
        if (this.value) {
        // alert("Ha seleccionado el servicio con id: "+id)
            var model = this.model;
            var method = 'get_base64_data';
            var args = {
                field_name: this.name,
                record_id: this.record.res_id
            }
            var call_kw = '/web/dataset/call_kw/' + model + '/' + method;
            session.rpc(call_kw, {
                model: model,
                method: method,
                kwargs: args,
                args: []
            }).then(res => {
            this.$el.empty();
            this.generateHtmlTable(res, 15);
            });
        }
    }
})

var CsvTable = AbstractField.extend({
    className: 'o_field_csv_table',
    supportedFieldTypes: ['binary'],
        convert_to_table: function(csv) {
      let rows = csv.split("\n");
      if (rows.length){
          rows = rows[rows.length-1] == "" ? rows.slice(0,-1) : rows;
      }
      let res = ``;
      let headers = [];
      let real_rows = [];
      switch (rows.length) {
        case 0:
          return "";
        case 1: {
          headers = rows[0].split(",");
          real_rows = [];
          break;
        }
        default: {
          headers = rows[0].split(",");
          real_rows = rows.slice(1).map((x) => x.split(","));
          break;
        }
      }
      return `<table class="o_list_view table table-condensed table-hover table-striped o_list_view_ungrouped">
      <thead>
        <tr>
          ${headers.map(x => this.header(x)).join("\n")}
        </tr>
      </thead>
      <tbody>
          ${real_rows.map(x => this.tbody(x)).join("\n")}
      </tbody>
    </table>`;
    },
header: function(element) {
  return `<th>${element}</th>`;
},
tbody: function(row) {
  return `<tr>${row.map(x => this.line(x)).join("\n")}</tr>`;
},
line: function (element) {
  return `<td>${element}</td>`;
},
generateHtmlTable: function(csvBloat) {
  const csv = window.atob(csvBloat);
  const html_string = this.convert_to_table(csv);
  const html_table = html_string != "" ? this.htmlToElement(html_string) :this.htmlToElement("<div></div>");
  return html_table;
},
htmlToElement: function(html) {
  var template = document.createElement("template");
  html = html.trim(); // Never return a text node of whitespace as the result
  template.innerHTML = html;
  return template.content.firstChild;
},
    render_csv_table: function(data){
        const new_node = this.generateHtmlTable(data);
        return new_node
    },
    _render: function () {
        if (this.value) {
        // alert("Ha seleccionado el servicio con id: "+id)
            var model = this.model;
            var method = 'get_base64_data';
            var args = {
                field_name: this.name,
                record_id: this.record.res_id
            }
            var call_kw = '/web/dataset/call_kw/' + model + '/' + method;
            session.rpc(call_kw, {
                model: model,
                method: method,
                kwargs: args,
                args: []
            }).then(res => {
            this.$el.empty().append(this.render_csv_table(res))
            });
        }
    }
     }
);


fieldRegistry.add('csv_table', CsvTable2)
return CsvTable2;
});
