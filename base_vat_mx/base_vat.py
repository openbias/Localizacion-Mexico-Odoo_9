# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import string
import datetime
import re

from openerp.fields import Char
from openerp.models import Model, api, _
from openerp.exceptions import Warning, UserError, RedirectWarning, ValidationError

   
class ResPartner(Model):
    _inherit = 'res.partner'

    vat = Char(string='TIN', help="Tax Identification Number. Fill it if the company is subjected to taxes. Used by the some of the legal statements.")
    

    @api.model
    def create(self, vals):
        if vals.get('vat',False):
            vat = '%s'%(vals['vat'])
            vals['vat'] = re.sub('[-,._  \t\n\r\f\v]','',vat)
        return super(ResPartner, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('vat',False):
            vat = '%s'%(vals['vat'])
            vals['vat'] = re.sub('[-,._  \t\n\r\f\v]','',vat)
        return super(ResPartner, self).write(vals)


    # @api.one
    # @api.constrains('vat')
    # def _check_unique_vat(self):
    #     if not self.vat:
    #         return True
    #     val = re.match("[A-Z&]{3,4}[0-9]{6}[A-Z&0-9]{3}", self.vat.upper()) and True or False
    #     return val

    @api.one
    @api.constrains('vat', 'parent_id', 'company_id')
    def check_vat_unique(self):
        if not self.vat:
            return True

        vat = '%s'%(self.vat)
        vat = re.sub('[-,._  \t\n\r\f\v]','', vat)

        if vat in ('XAXX010101000', 'XEXX010101000'):
            return True

        # actual [A-Z&]{3,4}[0-9]{6}[A-Z&0-9]{3}
        # [A-Z,Ñ,&]{3,4}[0-9]{2}[0-1][0-9][0-3][0-9][A-Z,0-9]?[A-Z,0-9]?[0-9,A-Z]?
        vat = re.match("[A-Z,Ñ,&]{3,4}[0-9]{2}[0-1][0-9][0-3][0-9][A-Z,0-9]?[A-Z,0-9]?[0-9,A-Z]?", vat.upper()) and True or False
        if vat == False:
            raise UserError(_('RFC mal formado'))

        # get first parent
        parent = self
        while parent.parent_id:
            parent = parent.parent_id

        same_vat_partners = self.search([
            ('vat', '=', vat),
            ('vat', '!=', False),
            ('company_id', '=', self.company_id.id),
        ])

        if same_vat_partners:
            related_partners = self.search([
                ('id', 'child_of', parent.id),
                ('company_id', '=', self.company_id.id),
            ])
            same_vat_partners = self.search([
                ('id', 'in', same_vat_partners.ids),
                ('id', 'not in', related_partners.ids),
                ('company_id', '=', self.company_id.id),
            ])
            partner_name = ''
            for partner in same_vat_partners:
                partner_name += '%s\n'%(partner.name)
            if same_vat_partners:
                raise UserError(_('Partner vat must be unique per company except on partner with parent/childe relationship.\nPartners with same vat and not related, are:\n %s!')%(partner_name) )
        return True

    @api.one
    def validate_vat(self):
        if self.vat:
            vat = '%s'%(self.vat)
            vat = re.sub('[-,._  \t\n\r\f\v]','', vat)
            self.write({'vat': vat})





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
