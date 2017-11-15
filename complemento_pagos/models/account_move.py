# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

from datetime import date, datetime
from pytz import timezone
import json

class AccountAbstractPayment(models.AbstractModel):
    _name = "account.abstract.payment"
    _inherit = "account.abstract.payment"

    formapago_id = fields.Many2one('cfd_mx.formapago', string=u'Forma de Pago')

class AccountRegisterPayments(models.TransientModel):
    _inherit = "account.register.payments"
    _description = "Register payments on multiple invoices"

    formapago_id = fields.Many2one('cfd_mx.formapago', string=u'Forma de Pago')

    def get_payment_vals(self):
        rec = super(AccountRegisterPayments, self).get_payment_vals()
        vals = {
            'formapago_id': self.formapago_id and self.formapago_id.id or None
        }
        rec.update(vals)
        return rec

class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = "account.payment"

    formapago_id = fields.Many2one('cfd_mx.formapago', string=u'Forma de Pago')
    
    def _create_payment_entry_pagos(self, amount, move):
        ctx = dict(self._context) or {}
        for aml in move.line_ids:
            invoice_ids = []
            if aml.credit > 0:
                for r in aml.matched_debit_ids:
                    if r.debit_move_id.invoice_id:
                        invoice_ids.append(r.debit_move_id.invoice_id)
            else:
                for r in aml.matched_credit_ids:
                    if r.credit_move_id.invoice_id:
                        if r.credit_move_id.invoice_id.uuid:
                            invoice_ids.append(r.credit_move_id.invoice_id)
            if len(invoice_ids):
                ctx['invoice_ids'] = invoice_ids
                aml.action_write_date_invoice_cfdi(aml.id)
                aml.with_context(**ctx).reconcile_create_cfdi()
        return True


    # def _create_payment_entry(self, amount):
    #     move = super(AccountPayment, self)._create_payment_entry(amount)
    #     context = self._context
    #     print "self.partner_type", self.partner_type
    #     print "self.journal_id.id", self.journal_id.id, self.env.user.company_id.cfd_mx_journal_ids.ids
    #     print miguelmiguel
    #     if self.partner_type == "customer" and self.journal_id.id in self.env.user.company_id.cfd_mx_journal_ids.ids:
    #         self.with_context(context)._create_payment_entry_pagos(amount, move)
    #     return move

    # @api.multi
    # def post(self):
    #     self = self.with_context(opt='post', payment_id=self, formapago_id=self.formapago_id)
    #     res = super(AccountPayment, self).post()
    #     return res

class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"

    formapago_id = fields.Many2one('cfd_mx.formapago', string=u'Forma de Pago')

    def action_validate_cfdi(self):
        ctx = dict(self._context) or {}
        cfdi = self.env['account.cfdi']
        user_id = self.env.user
        tz = user_id.tz
        message = ''
        if not self.journal_id.codigo_postal_id:
            message += 'No se definio Lugar de Exception (C.P.)'
        regimen_id = user_id.company_id.partner_id.regimen_id
        if not regimen_id:
            message += 'No se definio Regimen Fiscal para la Empresa'
        if not cfdi.valida_catcfdi('regimenFiscal', regimen_id.clave):
            message += 'Regimen Fiscal no corresponde al Catalogo SAT'
        if not tz:
            message += 'El usuario no tiene definido Zona Horaria'
        if not self.partner_id.vat:
            message += 'No se especifico el RFC para el Cliente'
        if not user_id.company_id.partner_id.vat:
            message += 'No se especifico el RFC para la Empresa'
        if not self.formapago_id:
            message += 'No se especifico el la forma de Pago'
        if message:
            raise UserError(message)
        return message

    def _create_payment_entry_pagos(self, move):
        ctx = dict(self._context) or {}
        for aml in move.line_ids:
            invoice_ids = []
            if aml.credit > 0:
                for r in aml.matched_debit_ids:
                    inv_id = r.debit_move_id.invoice_id
                    if inv_id:
                        if inv_id.uuid and inv_id.type == 'out_invoice':
                            invoice_ids.append(inv_id)
            else:
                for r in aml.matched_credit_ids:
                    inv_id = r.credit_move_id.invoice_id
                    if inv_id:
                        if inv_id.uuid and inv_id.type == 'out_invoice':
                            invoice_ids.append(inv_id)
            print "invoice_ids", invoice_ids
            if len(invoice_ids):
                ctx['invoice_ids'] = invoice_ids
                ctx['statement_line_id'] = self
                ctx['journal_id'] = self.journal_id
                aml.action_write_date_invoice_cfdi(aml.id)
                aml.with_context(**ctx).reconcile_create_cfdi()
        return True

    def process_reconciliation_pagos(self, move_id, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        context = self._context
        p = self._create_payment_entry_pagos(move_id)
        return True

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        message = self.action_validate_cfdi()
        res = super(account_bank_statement_line, self).process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec, new_aml_dicts=new_aml_dicts)
        self.process_reconciliation_pagos(res, counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec, new_aml_dicts=new_aml_dicts)
        return res



class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ['mail.thread', 'account.move.line', 'account.cfdi']

    number = fields.Char(string='Number')
    date_invoice = fields.Datetime(string='Invoice Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)

    def action_write_date_invoice_cfdi(self, inv_id):
        dtz = False
        if not self.date_invoice_cfdi:
            tz = self.env.user.tz or "UTC"
            cr = self._cr
            hora_factura_utc = datetime.now(timezone("UTC"))
            dtz = hora_factura_utc.astimezone(timezone(tz)).strftime("%Y-%m-%d %H:%M:%S")
            dtz = dtz.replace(" ", "T")
            cr.execute("UPDATE account_move_line SET date_invoice_cfdi='%s' WHERE id=%s "%(dtz, inv_id) )
            cr.commit()
        print "dtz", dtz
        return dtz

    @api.one
    def reconcile_create_cfdi(self):
        message = ""
        ctx = dict(self._context) or {}
        ctx['type'] = "pagos"
        print "ctx", ctx
        # res = self.with_context(**ctx).stamp(self)
        # if res.get('message'):
        #     message = res['message']
        # else:
        #     self.get_process_data(self, res.get('result'))

        try:
            res = self.with_context(**ctx).stamp(self)
            if res.get('message'):
                message = res['message']
            else:
                self.get_process_data(self, res.get('result'))
        except ValueError, e:
            message = str(e)
        except Exception, e:
            message = str(e)
        if message:
            message = message.replace("(u'", "").replace("', '')", "")
            self.action_raise_message("Error al Generar el XML \n\n %s "%( message.upper() ))
            return False
        return True





# class AccountBankStatementLine(models.Model):
#     _name = "account.bank.statement.line"
#     _inherit = "account.bank.statement.line"

#     @api.multi
#     def process_reconciliations(self, data):
#         self = self.with_context(opt='pagos')
#         res = super(AccountBankStatementLine, self).process_reconciliations(data)
#         return res



class AccountInvoice(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"

    @api.multi
    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        self = self.with_context(opt='pagos')
        res = super(AccountInvoice, self).register_payment(payment_line, writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        return res

    def get_cfdi_imp_pagados(self):
        inv = self
        amount_to_show = 0
        for payment in inv.payment_move_line_ids:
            if inv.type in ('out_invoice', 'in_refund'):
                amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in inv.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in inv.move_id.line_ids])
                if payment.matched_debit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in payment.matched_debit_ids]) and payment.matched_debit_ids[0].currency_id or False
            elif inv.type in ('in_invoice', 'out_refund'):
                amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in inv.move_id.line_ids])
                amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in inv.move_id.line_ids])
                if payment.matched_credit_ids:
                    payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in payment.matched_credit_ids]) and payment.matched_credit_ids[0].currency_id or False
            if payment_currency_id and payment_currency_id == inv.currency_id:
                amount_to_show += amount_currency
            else:
                amount_to_show += payment.company_id.currency_id.with_context(date=payment.date).compute(amount, inv.currency_id)
        return amount_to_show