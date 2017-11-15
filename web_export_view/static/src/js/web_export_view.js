//  @@@ web_export_view custom JS @@@

openerp.web_export_view = function (instance) {

    var _t = instance.web._t, QWeb = instance.web.qweb;

    instance.web.Sidebar.include({
        redraw: function () {
            var self = this;
            this._super.apply(this, arguments);
            if (self.getParent().ViewManager.active_view.type == 'list'){
    
                self.$el.find('.dropdown-menu').last().append(QWeb.render('AddExportViewMain', {widget: self}));
                self.$el.find('.oe_sidebar_export_view_xls').on('click', self.on_sidebar_export_view_xls);
            }
        },

        on_sidebar_export_view_xls: function () {
            // Select the first list of the current (form) view
            // or assume the main view is a list view and use that
            var self = this,
                view = this.getParent(),
                children = view.getChildren();
            if (children) {
                children.every(function (child) {
                    if (child.field && child.field.type == 'one2many') {
                        view = child.viewmanager.views.list.controller;
                        return false; // break out of the loop
                    }
                    if (child.field && child.field.type == 'many2many') {
                        view = child.list_view;
                        return false; // break out of the loop
                    }
                    return true;
                });
            }
            export_columns_keys = [];
            export_columns_names = [];
            $.each(view.visible_columns, function () {
                if (this.tag == 'field') {
                    // non-fields like `_group` or buttons
                    export_columns_keys.push(this.id);
                    export_columns_names.push(this.string);
                }
            });
            export_rows = [];
            rows = view.$el.find('.o_list_view.table.table-condensed  > tbody > tr');
            if (rows.length == 0 ){
                rows = view.$el.find('.oe_list_content > tbody > tr');
            }
            $.each(rows, function () {
                $row = $(this);
                // find only rows with data
                if ($row.attr('data-id')) {
                    export_row = [];
                    checked = $row.find('.o_list_record_selector input[type=checkbox]').val();
                    if (typeof checked === 'undefined' || checked === null){
                        checked = $row.find('.oe_list_record_selector input[type=checkbox]').val()
                    }
                    if (children && checked == "on") {
                        $.each(export_columns_keys, function () {
                            cell = $row.find('td[data-field="' + this + '"]').get(0);
                            text = cell.text || cell.textContent || cell.innerHTML || "";
                            if (cell.classList.contains("oe_list_field_float") || cell.classList.contains("oe_list_field_monetary") ) {
                                _.extend(instance.web._t.database.parameters, {
                                    monetary: '$',
                                });
                                var tmp2 = text.trim();
                                do {
                                    tmp = tmp2;
                                    tmp2 = tmp.replace(instance.web._t.database.parameters.monetary, "");
                                    tmp2 = tmp2.replace(instance.web._t.database.parameters.thousands_sep, "");
                                } while (tmp !== tmp2);
                                export_row.push(  Number(tmp2) );
                            }else if (cell.classList.contains("oe_list_field_boolean")) {
                                var data_id = $('<div>' + cell.innerHTML + '</div>');
                                if (data_id.find('input').get(0).checked) {
                                    export_row.push(_t("True"));
                                }
                                else {
                                    export_row.push(_t("False"));
                                }
                            }else if (cell.classList.contains("oe_list_field_integer")) {
                                var tmp2 = text.trim();
                                do {
                                    tmp = tmp2;
                                    tmp2 = tmp.replace(instance.web._t.database.parameters.thousands_sep, "");
                                } while (tmp !== tmp2);
                                export_row.push(parseInt(tmp2));
                            }else {
                                export_row.push(text.trim());
                            }
                        });
                        export_rows.push(export_row);
                    }
                }
            });

            $.blockUI();
            view.session.get_file({
                url: '/web/export/xls_view',
                data: {data: JSON.stringify({
                    model: view.model,
                    headers: export_columns_names,
                    rows: export_rows
                })},
                complete: $.unblockUI
            });
        }
    });

};
