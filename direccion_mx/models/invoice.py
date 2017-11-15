# -*- encoding: utf-8 -*-


from openerp.models import Model, TransientModel, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import re

from openerp.addons.cfd_mx.cfdi_utis.nodo import Nodo

class AccountInvoice(Model):
    _inherit = 'account.invoice'

    @api.multi
    def get_nodo_comprobante_emisor(self, comprobante):        
        version = self.company_id.cfd_mx_version
        ns = version == '3.2' and 'cfdi:' or ''

        partner_data = self.company_id.partner_id

        emisor = Nodo(ns+'Emisor', {
            'rfc': partner_data.vat or "",
            'nombre': partner_data.name or "",
        }, comprobante)

        domicilioFiscal = Nodo(ns+'DomicilioFiscal', {
            'calle': partner_data.street or "",
            'noExterior': partner_data.noExterior or "",
            'noInterior': partner_data.noInterior or "",
            'localidad': partner_data.ciudad_id and partner_data.ciudad_id.name or "",
            'colonia': partner_data.colonia_id and partner_data.colonia_id.name or "",
            'municipio': partner_data.municipio_id and partner_data.municipio_id.name or "",
            'estado': partner_data.state_id and partner_data.state_id.name or "",
            'pais': partner_data.country_id and partner_data.country_id.name or "",
            'codigoPostal': partner_data.zip or "",
        }, emisor)

        regimenFiscal = Nodo(ns+'RegimenFiscal', {
            'Regimen': partner_data.regimen_id and partner_data.regimen_id.name or ""
        }, emisor)

        return


    @api.multi
    def get_nodo_comprobante_receptor(self, comprobante):
        version = self.company_id.cfd_mx_version
        ns = version == '3.2' and 'cfdi:' or ''

        partner_data = self.partner_id
        receptor = Nodo(ns +'Receptor', {
            'rfc': partner_data.vat or "",
            'nombre': partner_data.name or "",
        }, comprobante)

        domicilio = Nodo(ns+'Domicilio', {
            'calle': partner_data.street or "",
            'noExterior': partner_data.noExterior or "",
            'noInterior': partner_data.noInterior or "",
            'localidad': partner_data.ciudad_id and partner_data.ciudad_id.name or "",
            'colonia': partner_data.colonia_id and partner_data.colonia_id.name or "",
            'municipio': partner_data.municipio_id and partner_data.municipio_id.name or "",
            'estado': partner_data.state_id and partner_data.state_id.name or "",
            'pais': partner_data.country_id and partner_data.country_id.name or "",
            'codigoPostal': partner_data.zip or "",
        }, receptor)
        return


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: