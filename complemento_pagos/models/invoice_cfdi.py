# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

class AccountCfdi(models.Model):
    _inherit = "account.move.line"

    ################################
    #
    # Account Payment
    #
    ################################
    def pagos_info_comprobante(self):
        ctx = dict(self._context) or {}
        obj = self.obj
        journal_id = obj.journal_id
        date_invoice = obj.date_invoice_cfdi
        if not obj.date_invoice_cfdi:
            date_invoice = obj.action_write_date_invoice_cfdi(obj.id)
        cfdi_comprobante = {
            "Version": "3.3",
            "Folio": self._get_folio(),
            "Fecha": date_invoice,
            "SubTotal": 0,
            "Moneda": 'XXX',
            "Total": 0,
            "TipoDeComprobante": 'P',
            "LugarExpedicion": journal_id.codigo_postal_id.name
        }
        if journal_id.serie:
            cfdi_comprobante['Serie'] = journal_id.serie or ''
        return cfdi_comprobante

    def pagos_info_emisor(self):
        obj = self.obj
        partner_data = obj.company_id.partner_id
        emisor_attribs = {
            'Rfc': partner_data.vat or "",
            'Nombre': partner_data.name or "",
            "RegimenFiscal": partner_data.regimen_id and partner_data.regimen_id.clave or ""
        }
        return emisor_attribs

    def pagos_info_receptor(self):
        ctx = dict(self._context) or {}
        obj = self.obj
        partner_data = obj.partner_id
        receptor_attribs = {
            'Rfc': partner_data.vat or "",
            'Nombre': partner_data.name or "",
            'UsoCFDI': 'P01'
        }
        if partner_data.es_extranjero:
            receptor_attribs['ResidenciaFiscal'] = partner_data.country_id.code_alpha3
            if partner_data.identidad_fiscal:
                receptor_attribs['NumRegIdTrib'] = partner_data.identidad_fiscal
        return receptor_attribs

    def pagos_info_conceptos(self):
        obj = self.obj
        cfdi_conceptos = []
        concepto_attribs = {
            "ClaveProdServ": "84111506",
            "Cantidad": 1,
            "ClaveUnidad": "ACT",
            "Descripcion": "Pago",
            "ValorUnitario": 0,
            "Importe": 0
        }
        cfdi_conceptos.append(concepto_attribs)
        return cfdi_conceptos

    # RfcEmisorCtaOrd
    # NomBancoOrdExt
    # CtaOrdenante
    # RfcEmisorCtaBen
    # CtaBeneficiario
    # TipoCadPago = 01
    # CertPago
    # CadPago
    # SelloPago
    def pagos_info_complemento(self):
        ctx = dict(self._context) or {}
        obj = self.obj
        cfdi_pagos = []
        DoctoRelacionado = []
        print "mmmmmmmmmmmmmmmmm", ctx

        payment_id = ctx.get("statement_line_id") and ctx["statement_line_id"] or None
        formapago_id = payment_id and payment_id.formapago_id or None
        
        tipocambio = None
        p_journal_id = "MXN" if payment_id.journal_id.currency_id.name in [False, None] else payment_id.journal_id.currency_id.name
        monto = '%.2f'%(abs(obj.credit))
        if p_journal_id != "MXN":
            monto = '%.2f'%(abs(obj.amount_currency))
            tipocambio = self._get_tipocambio(payment_id.date)
        pago_attribs = {
            "FechaPago": '%sT12:00:00'%(payment_id.date),
            "FormaDePagoP": formapago_id.clave or "01",
            "MonedaP": p_journal_id,
            "Monto": monto,
        }
        if tipocambio:
            pago_attribs['TipoCambioP'] = '%s'%(tipocambio)
        if obj.ref:
            pago_attribs['NumOperacion'] = obj.ref
        for inv in ctx.get("invoice_ids", []):
            if inv.uuid:
                TipoCambioDR = self._get_tipocambio(payment_id.date)
                ImpPagos = inv.get_cfdi_imp_pagados()
                ImpPagado =  (abs(obj.credit) / TipoCambioDR)
                if p_journal_id != inv.currency_id.name:
                    ImpPagado = abs(obj.amount_currency)
                if (p_journal_id == inv.currency_id.name or inv.currency_id.name == "MXN" ):
                    TipoCambioDR = 1
                ImpSaldoAnt = (inv.amount_total - (ImpPagos - ImpPagado))
                if ImpSaldoAnt == 0.0:
                    ImpSaldoAnt = inv.amount_total
                ImpSaldoInsoluto = inv.amount_total - ImpPagos
                docto_attribs = {
                    "IdDocumento": inv.uuid,
                    "Folio": inv.number,
                    "MonedaDR": inv.currency_id.name,
                    "MetodoDePagoDR": "PPD",
                    "NumParcialidad": u"%s"%(inv.parcialidad_pago or 1),
                    "ImpSaldoAnt": '%.2f'%ImpSaldoAnt,
                    "ImpPagado": '%.2f'%ImpPagado,
                    'ImpSaldoInsoluto': '%.2f'%(abs(ImpSaldoInsoluto))
                }
                print "TipoCambioDR", TipoCambioDR
                if TipoCambioDR and (inv.currency_id.name != "MXN" and p_journal_id != "MXN"):
                    docto_attribs['TipoCambioDR'] = '%s'%(TipoCambioDR)
                if inv.journal_id.serie:
                    docto_attribs['Serie'] = inv.journal_id.serie or ''
                DoctoRelacionado.append(docto_attribs)
        res = {
            'pago_attribs': pago_attribs,
            'docto_relacionados': DoctoRelacionado
        }
        return res


    def _get_tipocambio(self, date_invoice):
        model_obj = self.env['ir.model.data']
        tipocambio = 1.0
        if date_invoice:
            if self.currency_id.name=='MXN':
                tipocambio = 1.0
            else:
                tipocambio = model_obj.with_context(date=date_invoice).get_object('base', 'MXN').rate
                tipocambio = round(tipocambio, 4)
        return tipocambio
