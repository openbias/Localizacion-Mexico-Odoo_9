# -*- encoding: utf-8 -*-


from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import re

ADDRESS_FIELDS = ('street', 'street2', 'colonia_id', 'zip', 'city', 'ciudad_id', 'municipio_id', 'state_id', 'country_id')

class ResPartner(models.Model):
    _inherit = 'res.partner'    
    
    ciudad_id = fields.Many2one('res.country.state.ciudad', string='Ciudad')
    municipio_id = fields.Many2one('res.country.state.municipio', string='Municipio')
    colonia_id = fields.Many2one('res.country.state.municipio.colonia', string="Colonia", size=128)


    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {
                'value': {
                    'country_id': state.country_id.id,
                    'ciudad_id': None,
                    'municipio_id': None,
                    'colonia_id': None,
                    }
                }
        return {'value': {}}

    @api.multi
    def onchange_colonia(self, colonia_id):
        if colonia_id:
            colonia = self.env['res.country.state.municipio.colonia'].browse(colonia_id)
            municipio_id = colonia.municipio_id
            return {
                'value':{
                    'zip': colonia.cp,
                    'municipio_id': municipio_id.id,
                    'ciudad_id': municipio_id.ciudad_id.id or False, 
                    'state_id': municipio_id.state_id.id,
                    'country_id': municipio_id.state_id.country_id.id, 
                }
            }
        return {'value': {}}

    @api.multi
    def onchange_municipio(self, municipio_id):
        if municipio_id:
            municipio = self.env['res.country.state.municipio'].browse(municipio_id)
            state_id = municipio.state_id
            return {
                'value':{
                    'ciudad_id': municipio.ciudad_id.id or False,
                    'state_id': state_id.id,
                    'country_id': state_id.country_id.id, 
                }
            }
        return {'value': {}}

    @api.multi
    def onchange_ciudad(self, ciudad_id):
        if ciudad_id:
            ciudad = self.env['res.country.state.ciudad'].browse(ciudad_id)
            state_id = ciudad.state_id
            return {
                'value':{
                    'state_id': state_id and state_id.id or None,
                    'country_id': state_id and state_id.country_id and state_id.country_id.id or None, 
                }
            }
        return {'value': {}}

    @api.multi
    def onchange_zip(self, col_zip):
        res = {'value': {
                'zip': None,
                'municipio_id': None,
                'ciudad_id': None, 
                'state_id': None,
                'country_id': None, 
            }
        }
        if col_zip:
            colonia_ids = self.env['res.country.state.municipio.colonia'].search([('cp', '=', col_zip)])
            for colonia in colonia_ids:
                municipio_id = colonia.municipio_id
                res = {'value': {
                        'zip': colonia.cp,
                        'municipio_id': municipio_id.id,
                        'ciudad_id': municipio_id.ciudad_id.id or False, 
                        'state_id': municipio_id.state_id.id,
                        'country_id': municipio_id.state_id.country_id.id, 
                    }
                }
                break;
        return res


    def _address_fields(self, cr, uid, context=None):
        """ Returns the list of address fields that are synced from the parent
        when the `use_parent_address` flag is set. """
        return list(ADDRESS_FIELDS)

    def _display_address(self, cr, uid, address, without_company=False, context=None):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        address_format = address.country_id.address_format or \
              "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': address.state_id.code or '',
            'state_name': address.state_id.name or '',
            'country_code': address.country_id.code or '',
            'country_name': address.country_id.name or '',
            'company_name': address.parent_name or '',
            'colonia_name': address.colonia_id and address.colonia_id.name or '',
            'ciudad_name':  address.ciudad_id and address.ciudad_id.name or '',
            'municipio_name':  address.municipio_id and address.municipio_id.name or '',
        }
        for field in self._address_fields(cr, uid, context=context):
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: