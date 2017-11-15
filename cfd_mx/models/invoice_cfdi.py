# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

class AccountCfdi(models.Model):
    _inherit = "account.invoice"

    ################################
    #
    # Account Invoice
    #
    ################################
    def invoice_info_relacionados(self):
        obj = self.obj
        cfdi_relacionado = {}
        if self.uuid_relacionado_id:
            cfdi_relacionado["TipoRelacion"] = self.tiporelacion_id and self.tiporelacion_id.clave or ""
            cfdi_relacionado["uuid"] = self.uuid_relacionado_id and self.uuid_relacionado_id.uuid or ""
        return cfdi_relacionado


    def invoice_info_comprobante(self):
        obj = self.obj
        dp = obj.env['decimal.precision'].precision_get('Account')
        if obj.currency_id.name == 'MXN':
            rate = 1.0
            nombre = obj.currency_id.nombre_largo or 'pesos'
        else:
            model_data = obj.env["ir.model.data"]
            mxn_rate = model_data.get_object('base', 'MXN').rate
            rate = (1.0 / obj.currency_id.rate) * mxn_rate
            nombre = obj.currency_id.nombre_largo or ''

        date_invoice = obj.date_invoice_cfdi
        if not obj.date_invoice_cfdi:
            date_invoice = obj.action_write_date_invoice_cfdi(obj.id)
            
        cfdi_comprobante = {
            "Folio": obj.number,
            "Fecha": date_invoice,
            "FormaPago": obj.formapago_id and obj.formapago_id.clave or "99",
            "CondicionesDePago": obj.payment_term_id and obj.payment_term_id.name or 'CONDICIONES',
            "Moneda": obj.currency_id.name,
            "SubTotal": '%.2f'%(obj.price_subtotal_sat),
            "Total": '%.2f'%(obj.price_subtotal_sat - obj.price_discount_sat + obj.price_tax_sat),
            "TipoDeComprobante": obj.tipo_comprobante,
            "MetodoPago": obj.metodopago_id and obj.metodopago_id.clave or 'Pago en una sola exhibicion',
            "LugarExpedicion": obj.journal_id and obj.journal_id.codigo_postal_id and obj.journal_id.codigo_postal_id.name or '',
            "Descuento": '%.2f'%(0.0)
        }
        if obj.journal_id.serie:
            cfdi_comprobante['Serie'] = obj.journal_id.serie or ''
        if obj.price_discount_sat:
            cfdi_comprobante['Descuento'] = '%.2f'%(round(obj.price_discount_sat, dp))
        if obj.currency_id.name != 'MXN':
            cfdi_comprobante['TipoCambio'] = '%s'%(round(rate, 4))
        return cfdi_comprobante

    def invoice_info_emisor(self):
        obj = self.obj
        partner_data = obj.company_id.partner_id
        emisor_attribs = {
            'Rfc': partner_data.vat or "",
            'Nombre': partner_data.name or "",
            "RegimenFiscal": partner_data.regimen_id and partner_data.regimen_id.clave or ""
        }
        return emisor_attribs

    def invoice_info_receptor(self):
        obj = self.obj
        partner_data = obj.partner_id
        receptor_attribs = {
            'Rfc': partner_data.vat or "",
            'Nombre': partner_data.name or "",
            'UsoCFDI': obj.usocfdi_id and obj.usocfdi_id.clave or ''
        }
        if partner_data.es_extranjero == True:
            receptor_attribs['ResidenciaFiscal'] = partner_data.country_id.code_alpha3
            if partner_data.identidad_fiscal:
                receptor_attribs['NumRegIdTrib'] = partner_data.identidad_fiscal
        return receptor_attribs

    def invoice_info_conceptos(self):
        obj = self.obj
        dp = obj.env['decimal.precision']
        dp_account = dp.precision_get('Account')
        dp_product = dp.precision_get('Product Price')
        conceptos = []
        for line in obj.invoice_line_ids:
            ClaveProdServ = '01010101'
            concepto_attribs = {
                'ClaveProdServ': line.product_id and line.product_id.clave_prodser_id and line.product_id.clave_prodser_id.clave or ClaveProdServ,
                'NoIdentificacion': line.product_id and line.product_id.default_code or '',
                'Descripcion': line.name.replace('[', '').replace(']', '') or '',
                'Cantidad': '%s'%(round(line.quantity, dp_account)),
                'ClaveUnidad': line.uom_id and line.uom_id.clave_unidadesmedida_id and line.uom_id.clave_unidadesmedida_id.clave or '',
                'Unidad': line.uom_id and line.uom_id.name or '',
                'ValorUnitario': '%.2f'%(round(line.price_unit, dp_product)),
                'Importe': '%.2f'%( line.price_subtotal_sat ),
                'Descuento': '%.2f'%( line.price_discount_sat ),
                'Impuestos': {
                    'Traslado': [],
                    'Retenciones': []
                }
            }
            if line.numero_pedimento_sat:
                concepto_attribs['NumeroPedimento'] = line.numero_pedimento_sat
            if line.product_id.cuenta_predial:
                concepto_attribs['CuentaPredial'] = line.product_id.cuenta_predial
            for tax in line.invoice_line_tax_ids:
                tax_group = tax.tax_group_id
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                comp = tax.compute_all(price_unit, obj.currency_id, line.quantity, line.product_id, obj.partner_id)
                importe = comp['total_included'] - comp['total_excluded']
                TasaOCuota = '%.6f'%((round(abs(tax.amount), dp_account) / 100))
                impuestos = {
                    'Base': '%.2f'%(round( comp.get('base') , dp_account)),
                    'Impuesto': tax_group.cfdi_impuestos,
                    'TipoFactor': '%s'%(tax.cfdi_tipofactor),
                    'TasaOCuota': '%s'%(TasaOCuota),
                    'Importe': '%.2f'%(round(importe, dp_account))
                }
                if tax_group.cfdi_retencion:
                    concepto_attribs['Impuestos']['Retenciones'].append(impuestos)
                if tax_group.cfdi_traslado:
                    concepto_attribs['Impuestos']['Traslado'].append(impuestos)
            conceptos.append(concepto_attribs)
        cfdi_conceptos = conceptos
        return cfdi_conceptos

    def invoice_info_impuestos(self, conceptos):
        TotalImpuestosRetenidos = 0.00
        TotalImpuestosTrasladados = 0.00
        traslado_attribs = {}
        for concepto in conceptos:
            print "concepto['Impuestos']", concepto['Impuestos']
            for impuesto in concepto['Impuestos']:
                print "impuesto", impuesto
                if impuesto == 'Retenciones':
                    for ret in concepto['Impuestos'][impuesto]:
                        TotalImpuestosRetenidos += float(ret['Importe'])
                        if not ret['Impuesto'] in traslado_attribs.keys():
                            traslado_attribs[ ret['Impuesto'] ] = {
                                'Importe': '%s'%(0.0)
                            }
                        importe = float(traslado_attribs[ ret['Impuesto'] ]['Importe']) + float(ret['Importe'])
                        traslado_attribs[ ret['Impuesto'] ] = {
                            'Impuesto': float(ret['Impuesto']),
                            'TipoFactor': ret['TipoFactor'],
                            'TasaOCuota': ret['TasaOCuota'],
                            'Importe': '%s'%(importe)
                        }
                if impuesto == 'Traslado':
                    for tras in concepto['Impuestos'][impuesto]:
                        TotalImpuestosTrasladados += float(tras['Importe'])
                        if not tras['Impuesto'] in traslado_attribs.keys():
                            traslado_attribs[ tras['Impuesto'] ] = {
                                'Importe': '%s'%(0.0)
                            }
                        importe = float(traslado_attribs[tras['Impuesto']]['Importe']) + float(tras['Importe'])
                        traslado_attribs[ tras['Impuesto'] ] = {
                            'Impuesto': tras['Impuesto'],
                            'TipoFactor': tras['TipoFactor'],
                            'TasaOCuota': tras['TasaOCuota'],
                            'Importe': '%.2f'%(importe)
                        }
        print "traslado_attribs", traslado_attribs
        cfdi_impuestos = {
            'TotalImpuestosRetenidos': '%.2f'%(TotalImpuestosRetenidos),
            'TotalImpuestosTrasladados': '%.2f'%(TotalImpuestosTrasladados),
            'traslado_attribs': traslado_attribs
        }
        return cfdi_impuestos