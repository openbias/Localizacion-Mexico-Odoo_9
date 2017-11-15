# -*- encoding: utf-8 -*-


from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class Ciudad(models.Model):
    _name = 'res.country.state.ciudad'
    
    state_id = fields.Many2one('res.country.state', 
        string='Estado', required=True)
    name = fields.Char(string='Name', size=256, required=True)


class Municipio(models.Model):
    _name = 'res.country.state.municipio'
    
    state_id = fields.Many2one('res.country.state', 
        string='State', required=True)
    ciudad_id = fields.Many2one('res.country.state.ciudad', string='City')
    name = fields.Char('Name', size=64, required=True)
    clave_sat = fields.Char("Clave SAT")
    
    
class Colonia(models.Model):
    _name = 'res.country.state.municipio.colonia'
    
    municipio_id = fields.Many2one('res.country.state.municipio', 
        string='Municipio', required=True)
    name = fields.Char(string='Name', size=256, required=True)
    cp = fields.Char(string='Código Postal', size=10)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
