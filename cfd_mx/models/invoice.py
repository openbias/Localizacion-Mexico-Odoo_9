# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
# from odoo.addons.cfd_mx.models.cfd_util import CfdiUtils
# from odoo.addons.cfd_mx.models.cfdi_validate import *

import time
from datetime import date, datetime, timedelta
from pytz import timezone, utc
import base64


import logging
_logger = logging.getLogger(__name__)



class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"
    _description = "Credit Note"

    tiporelacion_id = fields.Many2one('cfd_mx.tiporelacion', string=u'Tipo de Relacion', copy="False")

    @api.multi
    def compute_refund(self, mode='refund'):
        ctx = dict(self.env.context)
        ctx["tiporelacion_id"] = self.tiporelacion_id.id
        res = super(AccountInvoiceRefund, self.with_context(**ctx)).compute_refund(mode=mode)
        return res



class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice')
    def _compute_price_sat(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price_subtotal_sat = self.price_unit # * self.quantity
        discount =  ((self.discount or 0.0) / 100.0) * price_subtotal_sat
        price = (price_subtotal_sat - discount)
        taxes = {}
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, self.currency_id, self.quantity, self.product_id, self.partner_id)
        
        self.price_tax_sat = taxes.get('total_included', 0.00) - taxes.get('total_excluded', 0.00)
        self.price_subtotal_sat = self.price_unit * self.quantity
        self.price_discount_sat = discount * self.quantity

    price_subtotal_sat = fields.Monetary(string='Amount (SAT)', readonly=True, compute='_compute_price_sat', default=0.00)
    price_tax_sat = fields.Monetary(string='Tax (SAT)', readonly=True, compute='_compute_price_sat', default=0.00)
    price_discount_sat = fields.Monetary(string='Discount (SAT)', readonly=True, compute='_compute_price_sat', default=0.00)
    numero_pedimento_sat = fields.Char(string='Numero de Pedimento', help="Informacion Aduanera. Numero de Pedimento")

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'account.cfdi']

    @api.one
    @api.depends(
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.price_subtotal_sat',
        'invoice_line_ids.price_tax_sat',
        'invoice_line_ids.price_discount_sat',
        'tax_line_ids.amount',
        'currency_id',
        'company_id',
        'date_invoice',
        'type')
    def _compute_price_sat(self):
        descuento = 0.00
        impuestos = 0.00
        subtotal = 0.00
        for line in self.invoice_line_ids:
            impuestos += line.price_tax_sat
            subtotal += line.price_subtotal_sat
            if line.discount:
                descuento += line.price_discount_sat
        
        self.price_subtotal_sat = subtotal
        self.price_tax_sat = impuestos
        self.price_discount_sat = descuento


    @api.one
    def _default_uso_cfdi_id(self):
        public = self.env.ref('cfd_mx.cfd_mx_usocfdi_G01')
        return public

    @api.one
    def _get_parcialidad_pago(self):
        self.parcialidad_pago = len(self.payment_move_line_ids) or 0
        self.pagos = True if len(self.payment_move_line_ids) != 0 else False



    pagos = fields.Boolean(string="Pagos", default=False, copy=False, compute='_get_parcialidad_pago')
    parcialidad_pago = fields.Integer(string="No. Parcialidad Pago", compute='_get_parcialidad_pago')
    uuid_relacionado_id = fields.Many2one('account.invoice', string=u'UUID Relacionado', domainf=[("type", "in", ("out_invoice", "out_refund") ), ("timbrada", "=", True), ("uuid", "!=", None)])
    tiporelacion_id = fields.Many2one('cfd_mx.tiporelacion', string=u'Tipo de Relacion', copy="False")

    price_subtotal_sat = fields.Monetary(string='Amount (SAT)', readonly=True, compute='_compute_price_sat')
    price_tax_sat = fields.Monetary(string='Tax (SAT)', readonly=True, compute='_compute_price_sat')
    price_discount_sat = fields.Monetary(string='Discount (SAT)', readonly=True, compute='_compute_price_sat')
    xml_cfdi_sinacento = fields.Boolean(related="partner_id.xml_cfdi_sinacento", string='XML CFDI sin acentos')
    internal_number = fields.Char(string='Invoice Number', size=32, readonly=True, copy=False, help="Unique number of the invoice, computed automatically when the invoice is created.")
    usocfdi_id = fields.Many2one('cfd_mx.usocfdi', string="Uso de Comprobante CFDI", required=False)
    metodopago_id = fields.Many2one('cfd_mx.metodopago', string=u'Metodo de Pago')

    # Quitar en Futuras Versiones
    cuentaBanco = fields.Char(string='Ultimos 4 digitos cuenta', size=4, default='')
    anoAprobacion = fields.Integer(string=u"Año de aprobación")
    noAprobacion = fields.Char(string="No. de aprobación")
    tipopago_id = fields.Many2one('cfd_mx.tipopago', string=u'Forma de Pago')


    @api.onchange('date_invoice')
    def _onchange_date_invoice(self):
        if not self.date_invoice:
            return {}
        field_now = fields.Datetime.now()
        self.date_invoice_cfdi = self.convert_datetime_timezone(field_now, "UTC", self.env.user.tz)

    @api.onchange('uuid_relacionado_id')
    def _onchange_date_invoice(self):
        if not self.uuid_relacionado_id:
            return {}
        self.uuid_egreso = self.uuid_relacionado_id.uuid


    @api.onchange('partner_id', 'formapago_id')
    def onchange_metododepago(self):
        if not self.partner_id:
            self.update({
                'formapago_id': False,
                'cuentaBanco': False,
                'metodopago_id': False,
                'usocfdi_id': False
            })
            return

        if not self.usocfdi_id:
            self.usocfdi_id = self.partner_id.usocfdi_id and self.partner_id.usocfdi_id.id or None 
        if not self.metodopago_id:
            self.metodopago_id = self.partner_id.metodopago_id and self.partner_id.metodopago_id.id or None 
        if not self.formapago_id:
            self.formapago_id = self.partner_id.formapago_id and self.partner_id.formapago_id.id or None
        cuenta = ''
        if self.formapago_id and self.formapago_id.banco:
            if not self.partner_id:
                raise UserError("No se ha definido cliente")
            if self.partner_id.bank_ids:
                for bank in self.partner_id.bank_ids:
                    cuenta = bank.acc_number[-4:]
                    break
            else:
                cuenta = 'xxxx'
        self.cuentaBanco = cuenta
        return {}

    @api.model
    def create(self, vals):
        onchanges = {
            'onchange_metododepago': ['partner_id', 'formapago_id', 'metodopago_id', 'cuentaBanco'],
        }
        for onchange_method, changed_fields in onchanges.items():
            if any(f not in vals for f in changed_fields):
                invoice = self.new(vals)
                getattr(invoice, onchange_method)()
                for field in changed_fields:
                    if field not in vals and invoice[field]:
                        vals[field] = invoice._fields[field].convert_to_write(invoice[field], invoice)
        invoice = super(AccountInvoice, self.with_context(mail_create_nolog=True)).create(vals)
        if invoice.type == 'out_invoice':
            invoice.tipo_comprobante = "I"
            # invoice.usocfdi_id = invoice.partner_id.usocfdi_id and invoice.partner_id.usocfdi_id.id or None
            if not invoice.usocfdi_id:
                invoice.usocfdi_id = invoice.partner_id.usocfdi_id and invoice.partner_id.usocfdi_id.id or None
            if not invoice.formapago_id:
                invoice.formapago_id = invoice.partner_id.formapago_id and invoice.partner_id.formapago_id.id or None
            if not invoice.metodopago_id:
                invoice.metodopago_id = invoice.partner_id.metodopago_id and invoice.partner_id.metodopago_id.id or None
        if invoice.type == 'out_refund':
            invoice.tipo_comprobante = "E"
        return invoice

    @api.multi
    def action_move_create(self):
        res = super(AccountInvoice, self).action_move_create()
        self.write({'internal_number': self.number})
        return True

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        ctx = dict(self.env.context)
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice=date_invoice, date=date, description=description, journal_id=journal_id)
        values['uuid_relacionado_id'] = invoice.id
        values['cuentaBanco'] = invoice.cuentaBanco
        values['formapago_id'] = invoice.formapago_id and invoice.formapago_id.id or None
        values["metodopago_id"] = invoice.metodopago_id and invoice.metodopago_id.id or None
        values["usocfdi_id"] = invoice.usocfdi_id and invoice.usocfdi_id.id or None
        values["tiporelacion_id"] = ctx.get("tiporelacion_id", None) or None
        values['uuid_egreso'] = invoice.uuid
        values['tipo_comprobante'] = 'E'
        return values
  
    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Vendor Refund'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.number or inv.internal_number or TYPES[inv.type], inv.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        recs = super(AccountInvoice, self).name_search(name, args=args, operator=operator, limit=limit)
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('internal_number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
   
    # Crea xml
    # @api.multi
    # def invoice_validate(self):
    #     print "mmmmmmmmmmmmmmmmm"
    #     for invoice in self:
    #         self.action_write_date_invoice_cfdi(invoice.id)
    #     for invoice in self:
    #         invoice.action_create_cfd()
    #     res = super(AccountInvoice, self).invoice_validate()
    #     return res

    def action_write_date_invoice_cfdi(self, inv_id):
        dtz = False
        if not self.date_invoice_cfdi:
            tz = self.env.user.tz
            if not tz:
                message = '<li>El usuario no tiene definido Zona Horaria</li>'
                self.action_raise_message(message)
                return message
            cr = self._cr
            hora_factura_utc = datetime.now(timezone("UTC"))
            dtz = hora_factura_utc.astimezone(timezone(tz)).strftime("%Y-%m-%d %H:%M:%S")
            dtz = dtz.replace(" ", "T")
            cr.execute("UPDATE account_invoice SET date_invoice_cfdi='%s' WHERE id=%s "%(dtz, inv_id) )
            # cr.commit()
        return dtz

    @api.multi
    def action_validate_cfdi(self):
        cfdi = self
        tz = self.env.user.tz
        message = ''
        if not self.tipo_comprobante:
            message += '<li>No se definio Tipo Comprobante</li>'
        if not self.journal_id.codigo_postal_id:
            message += '<li>No se definio Lugar de Exception (C.P.)</li>'
        if not self.payment_term_id:
            message += '<li>No se definio Condiciones de Pago</li>'
        if not self.formapago_id:
            message += '<li>No se definio Forma de Pago</li>'
        if not cfdi.valida_catcfdi('formaPago', self.formapago_id.clave):
            message += '<li>Forma de Pago no corresponde al Catalogo SAT</li>'
        if not self.metodopago_id:
            message += '<li>No se definio Metodo de Pago</li>'
        if not cfdi.valida_catcfdi('metodoPago', self.metodopago_id.clave):
            message += '<li>Metodo de Pago no corresponde al Catalogo SAT</li>'
        if not self.usocfdi_id:
            message += '<li>No se definio Uso CFDI</li>'
        if not cfdi.valida_catcfdi('usoCdfi', self.usocfdi_id.clave):
            message += '<li>Uso CFDI no corresponde al Catalogo SAT</li>'
        regimen_id = self.company_id.partner_id.regimen_id
        if not regimen_id:
            message += '<li>No se definio Regimen Fiscal para la Empresa</li>'
        if not cfdi.valida_catcfdi('regimenFiscal', regimen_id.clave):
            message += '<li>Regimen Fiscal no corresponde al Catalogo SAT</li>'
        if not tz:
            message += '<li>El usuario no tiene definido Zona Horaria</li>'
        if not self.partner_id.vat:
            message += '<li>No se especifico el RFC para el Cliente</li>'
        if not self.company_id.partner_id.vat:
            message += '<li>No se especifico el RFC para la Empresa</li>'
        for line in self.invoice_line_ids:
            if not line.uom_id.clave_unidadesmedida_id.clave:
                message += '<li>Favor de Configurar la Clave Unidad SAT "%s"</li>'%(line.uom_id.name)
            for tax in line.invoice_line_tax_ids:
                if not tax.tax_group_id.cfdi_impuestos:
                    message += '<li>El impuesto %s no tiene categoria CFD</li>'%()
        cfdi.action_raise_message(message)
        return message

    @api.one
    def action_create_cfd(self):
        tz = self.env.user.tz
        if self.uuid:
            return True
        if not self.journal_id.id in self.company_id.cfd_mx_journal_ids.ids:
            return True
        if self.type.startswith("in"):
            return True
        message = self.action_validate_cfdi()

        res = self.with_context({'type': 'invoice'}).stamp(self)
        print "resssssssssssssss", res
        if res.get('message'):
            message = res['message']
        else:
            self.get_process_data(self, res.get('result'))


        # try:
        #     res = self.with_context({'type': 'invoice'}).stamp(self)
        #     if res.get('message'):
        #         message = res['message']
        #     else:
        #         self.get_process_data(self, res.get('result'))
        # except ValueError, e:
        #     message = str(e)
        # except Exception, e:
        #     message = str(e)
        if message:
            message = message.replace("(u'", "").replace("', '')", "")
            self.action_raise_message("Error al Generar el XML \n\n %s "%( message.upper() ))
            return False
        return True


    # Cancela xml
    @api.multi
    def action_cancel(self):
        ctx = {'state': self.state}
        res = super(AccountInvoice, self).action_cancel()
        self.with_context(**ctx).action_cancel_cfdi()
        return res

    @api.multi
    def action_cancel_cfdi(self):
        context = dict(self._context) or {}
        if not self.uuid:
            return True
        if context.get('state') == 'draft':
            return True
        if self.type.startswith("in"):
            return True
        if self.journal_id.id not in self.company_id.cfd_mx_journal_ids.ids:
            return True
        message = ''
        try:
            res = self.cancel(self)
            if res.get('message'):
                message = res['message']
            else:
                acuse = res["result"].get("Acuse")
                self.write({
                    'mandada_cancelar': True, 
                    'mensaje_pac': """
                    <strong>Fecha: </strong> %s<br />
                    <strong>Folios</strong>%s<br />
                    <strong>XML Acuse</strong><pre lang="xml"><code>%s</code></pre>
                    """%(res["result"].get("Fecha"), res["result"].get("Folios"), acuse)
                })

                attachment_obj = self.env['ir.attachment']
                fname = "cancelacion_cfd_%s.xml"%(self.internal_number or "")
                attachment_values = {
                    'name': fname,
                    'datas': base64.b64encode(acuse),
                    'datas_fname': fname,
                    'description': 'Cancelar Comprobante Fiscal Digital',
                    'res_model': self._name,
                    'res_id': self.id,
                    'type': 'binary'
                }
                attachment_obj.create(attachment_values)


        except ValueError, e:
            message = str(e)
        except Exception, e:
            message = str(e)
        if message:
            message = message.replace("(u'", "").replace("', '')", "")
            self.action_raise_message("Error al Generar el XML \n\n %s "%( message.upper() ))
            return False
        return True

    @api.multi
    def get_comprobante_addenda(self):
        context = dict(self._context) or {}
        dict_addenda = {}
        Addenda = self.env['cfd_mx.conf_addenda']
        for conf_addenda in Addenda.search([('partner_ids', 'in', self.partner_id.ids)]):
            context.update({'model_selection': conf_addenda.model_selection})
            dict_addenda = conf_addenda.with_context(**context).create_addenda(self)
        return dict_addenda


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values
            /!\ for x2many field, this onchange return command instead of ids
        """
        res = super(MailComposeMessage, self).onchange_template_id(template_id,
                composition_mode, model, res_id)
        if self.env.context.get('active_model', False) == 'account.invoice':
            invoice = self.env["account.invoice"].browse(self.env.context['active_id'])
            if not invoice.number:
                return res

            xml_name = "cfd_" + invoice.number + ".xml"
            xml_id = self.env["ir.attachment"].search([('name', '=', xml_name)])
            if xml_id:
                res['value'].setdefault('attachment_ids', []).append(xml_id[0].id)

        return res


class report_invoice_mx(models.AbstractModel):
    _name = 'report.report_invoice_mx'
    
    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        model_obj = self.env['ir.model.data']
        report = report_obj._get_report_from_name('report_invoice_mx')
        docs = self.env[ report.model ].browse(self._ids)

        tipo_cambio = {}
        for invoice in docs:
            tipo_cambio[invoice.id] = 1.0
            if invoice.uuid:
                if invoice.currency_id.name=='MXN':
                    tipo_cambio[invoice.id] = 1.0
                else:
                    tipo_cambio[invoice.id] = model_obj.with_context(date=invoice.date_invoice).get_object('base', 'MXN').rate

        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': docs,
            'tipo_cambio': tipo_cambio
        }
        return report_obj.render('cfd_mx.report_invoice_mx',  docargs)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: