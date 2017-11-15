# -*- coding: utf-8 -*-

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models, _


from openerp.addons.report_xlsx.report.report_xlsx import ReportXlsx


class AccountChartReportPDF(models.AbstractModel):
    _name = 'report.accountchart_report_pdf'

    @api.multi
    def data_render(self, data):
        Account = self.env['account.account']
        

        initial_res = []
        if data.get('is_partner', False):
            acc = Account.with_context(**data).browse(data.get('account_id'))
            acc_id = acc.id
            acc_item = {
                'type': 'view',
                'name': '[%s] %s'%(acc.code, acc.name),
                'initial': acc.initial,
                'debit': acc.debit,
                'credit': acc.credit,
                'balance': acc.balance
            }
            initial_res.append(acc_item)

            if data.get('partner_ids'):
                Partner = self.env['res.partner']
                partner_ids = Partner.with_context(**data).search([('id', 'in', data.get('partner_ids'))])
                total_initial, total_debit, total_credit, total_balance = 0.0, 0.0, 0.0, 0.0

                indx = 0
                for partner in partner_ids:
                    context = data.copy()
                    context['partner_id'] = partner.id
                    account_id = Account.with_context(**context).browse(acc_id)
                    acc_item = {
                        'type': 'normal',
                        'name': partner.name,
                        'initial': account_id.initial,
                        'debit': account_id.debit,
                        'credit': account_id.credit,
                        'balance': account_id.balance
                    }
                    initial_res.append(acc_item)
                    total_initial += account_id.initial or 0.0
                    total_debit += account_id.debit or 0.0
                    total_credit += account_id.credit or 0.0
                    total_balance += account_id.balance or 0.0


                context = data.copy()
                context['not_partner_id'] = True
                account_id = Account.with_context(**context).browse(acc_id)
                acc_item = {
                    'type': 'normal',
                    'name': '...',
                    'initial': account_id.initial,
                    'debit': account_id.debit,
                    'credit': account_id.credit,
                    'balance': account_id.balance
                }
                initial_res.append(acc_item)
                total_initial += account_id.initial or 0.0
                total_debit += account_id.debit or 0.0
                total_credit += account_id.credit or 0.0
                total_balance += account_id.balance or 0.0

                acc_item = {
                    'type': 'view',
                    'name': 'Total',
                    'initial': total_initial,
                    'debit': total_debit,
                    'credit': total_credit,
                    'balance': total_balance
                }
                initial_res.append(acc_item)

        else:
            account_ids = Account.with_context(**data).search([])
            for acc in account_ids:
                acc_item = {
                    'type': acc.type,
                    'level': acc.level,
                    'code': acc.code,
                    'name': acc.name,
                    'initial': acc.initial,
                    'debit': acc.debit,
                    'credit': acc.credit,
                    'balance': acc.balance
                }
                initial_res.append(acc_item)
        return initial_res

    @api.multi
    def render_html(self, data):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'data': data,
            'Accounts': self.data_render(data)
        }
        return self.env['report'].render('gts_coa_hierarchy_v9.accountchart_report_pdf', docargs)


class AccountChartReportXlsx(ReportXlsx):
    _name = 'report.accountchart_report_xlsx'

    def generate_xlsx_report(self, workbook, data, models):
        company_id = self.env.user.company_id        
        workbook.set_properties({
            'title': _('Account Chart'),
            'subject': _('Account Chart'),
            'author': 'OpenBias',
            'manager': 'Odoo',
            'company': company_id.name,
            'category': 'Reportes Financieros',
            'comments': 'Reportes Financieros'
        })

        title_company = workbook.add_format({'font_name':'Arial', 'font_size':18, 'bold':1, 'align':'center', 'valign':'vcenter', 'color':'#032C46'})
        header_format = workbook.add_format({'font_name':'Arial', 'font_size':12, 'bold':1, 'italic':0, 'align':'center', 'valign':'vcenter', 'fg_color':'#AAAAAA', 'color':'#FFFFFF', 'bottom': 2, 'bottom_color':'#AAAAAA', 'top': 2, 'top_color':'#AAAAAA' })
        string_format = workbook.add_format({'font_name':'Trebuchet MS', 'font_size':10, 'align':'left', 'valign':'vcenter', 'fg_color':'#F2F2F2', 'bottom': 4, 'bottom_color':'#D9D9D9'})
        string_format_01 = workbook.add_format({'font_name':'Trebuchet MS', 'font_size':10, 'bold':1, 'align':'left', 'valign':'vcenter', 'fg_color':'#F2F2F2', 'bottom': 4, 'bottom_color':'#D9D9D9'})
        string_format_02 = workbook.add_format({'font_name':'Trebuchet MS', 'font_size':10, 'align':'left', 'valign':'vcenter', 'fg_color':'#FFFFFF', 'bottom': 4, 'bottom_color':'#D9D9D9'})
        string_format_03 = workbook.add_format({'font_name':'Trebuchet MS', 'font_size':10, 'align':'left', 'valign':'vcenter', 'fg_color':'white', 'bottom': 4, 'bottom_color':'#D9D9D9', 'color': 'blue'})
        money_format = workbook.add_format({'font_name':'Trebuchet MS', 'font_size':10, 'align':'right', 'valign':'vcenter', 'num_format':'$#,##0.00;[RED]-$#,##0.00', 'fg_color':'white', 'bottom': 4, 'bottom_color':'#D9D9D9'})

        for obj in models:
            data = obj.read([])[0]
            ctx = obj._build_contexts(data)

            # One sheet by
            sheet = workbook.add_worksheet( _('Account Chart') )
            sheet.hide_gridlines(2)
            sheet.freeze_panes(9, 0)

            target_move = _('Todas las Entradas')
            if ctx['state'] == 'all':
                target_move = _('Todas las Entradas')
            elif ctx['state'] == 'posted':
                target_move = _('Todas las Entradas Posteadas')

            #header
            sheet.merge_range('A1:F1', company_id.name, title_company)
            sheet.merge_range('A3:F3', _('Balanza de Comprobacion'), title_company)
            sheet.write_string(4, 1, _('Movimientos:'), string_format_01)            
            sheet.write_string(4, 3, _('Fecha Inicial :'), string_format_01)
            sheet.write_string(5, 3, _('Fecha Final :'), string_format_01)

            sheet.write_string(4, 2, target_move, string_format_02)
            sheet.write_string(4, 4, ctx['date_from'], string_format_02)
            sheet.write_string(5, 4, ctx['date_to'], string_format_02)

            if ctx.get('is_partner', False):
                sheet.set_column('A:A', 35)
                sheet.set_column('B:F', 20)


                Account = self.env['account.account']
                acc = Account.with_context(**ctx).browse(ctx.get('account_id'))
                h_balance = ['Total', _('Inicial'), _('Debito'), _('Credito'), _('Balance')]
                sheet.write_row('A8', h_balance, header_format)
                # Start from the first cell below the headers.
                row = 8
                col = 0
                acc_id = acc.id
                sheet.write_rich_string('A%s'%(row + 1), string_format_03, '[%s] %s'%(acc.code, acc.name))
                sheet.write_number(row, col + 1, acc.initial, money_format)
                sheet.write_number(row, col + 2, acc.debit, money_format)
                sheet.write_number(row, col + 3, acc.credit, money_format)
                sheet.write_number(row, col + 4, acc.balance, money_format)
                row += 1

                if ctx.get('partner_ids'):
                    Partner = self.env['res.partner']
                    partner_ids = Partner.with_context(**ctx).search([('id', 'in', ctx.get('partner_ids'))])
                    total_initial, total_debit, total_credit, total_balance = 0.0, 0.0, 0.0, 0.0
                    for partner in partner_ids:
                        context = ctx.copy()
                        context['partner_id'] = partner.id
                        account_id = Account.with_context(**context).browse(acc_id)
                        
                        sheet.write_string(row, col, '%s'%(partner.name), string_format)
                        sheet.write_number(row, col + 1, account_id.initial, money_format)
                        sheet.write_number(row, col + 2, account_id.debit, money_format)
                        sheet.write_number(row, col + 3, account_id.credit, money_format)
                        sheet.write_number(row, col + 4, account_id.balance, money_format)

                        total_initial += account_id.initial or 0.0
                        total_debit += account_id.debit or 0.0
                        total_credit += account_id.credit or 0.0
                        total_balance += account_id.balance or 0.0
                        row += 1



                context = ctx.copy()
                context['not_partner_id'] = True
                acc = Account.with_context(**context).browse(acc_id)
                sheet.write_string(row, col, ' ', string_format)
                sheet.write_number(row, col + 1, acc.initial, money_format)
                sheet.write_number(row, col + 2, acc.debit, money_format)
                sheet.write_number(row, col + 3, acc.credit, money_format)
                sheet.write_number(row, col + 4, acc.balance, money_format)
                total_initial += acc.initial or 0.0
                total_debit += acc.debit or 0.0
                total_credit += acc.credit or 0.0
                total_balance += acc.balance or 0.0
                row += 1

                acc = Account.with_context(**ctx).browse(ctx.get('account_id'))
                if ctx.get('partner_ids'):
                    sheet.write_string(row, col, 'Total', string_format_03)
                    sheet.write_number(row, col + 1, total_initial, money_format)
                    sheet.write_number(row, col + 2, total_debit, money_format)
                    sheet.write_number(row, col + 3, total_credit, money_format)
                    sheet.write_number(row, col + 4, total_balance, money_format)
            else:
                sheet.set_column('B:B', 35)
                sheet.set_column('C:F', 20)

                h_balance = [_('Nivel'), _('Cuenta'), _('Inicial'), _('Debito'), _('Credito'), _('Balance')]
                sheet.write_row('A8', h_balance, header_format)
                # Start from the first cell below the headers.
                row = 8
                col = 0
                total_initial, total_debit, total_credit, total_balance = 0.0, 0.0, 0.0, 0.0
                Account = self.env['account.account']
                account_ids = Account.with_context(**ctx).search([])
                for acc in account_ids:
                    level_ident = '    '* (acc.level - 1)

                    if acc.type == 'view':
                        style_type = string_format_03
                    else:
                        style_type = string_format

                    sheet.write_number(row, col, acc.level, string_format)
                    sheet.write_rich_string('B%s'%(row + 1), string_format, level_ident, style_type, '%s [%s] %s'%(level_ident, acc.code, acc.name))
                    sheet.write_number(row, col + 2, acc.initial, money_format)
                    sheet.write_number(row, col + 3, acc.debit, money_format)
                    sheet.write_number(row, col + 4, acc.credit, money_format)
                    sheet.write_number(row, col + 5, acc.balance, money_format)
                    row += 1

                    if acc.type != 'view':
                        total_initial += acc.initial or 0.0
                        total_debit += acc.debit or 0.0
                        total_credit += acc.credit or 0.0
                        total_balance += acc.balance or 0.0

                sheet.write_string(row, col, ' ', string_format)
                sheet.write_string(row, col + 1, 'Total', string_format)
                sheet.write_number(row, col + 2, total_initial, money_format)
                sheet.write_number(row, col + 3, total_debit, money_format)
                sheet.write_number(row, col + 4, total_credit, money_format)
                sheet.write_number(row, col + 5, total_balance, money_format)

AccountChartReportXlsx('report.accountchart_report_xlsx', 'account.chart')