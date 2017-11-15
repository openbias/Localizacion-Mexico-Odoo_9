# -*- encoding: utf-8 -*-
############################################################################
#    Module for OpenERP, Open Source Management Solution
#
#    Copyright (c) 2013 Zenpar - http://www.zeval.com.mx/
#    All Rights Reserved.
############################################################################
#    Coded by: jsolorzano@zeval.com.mx
#    Manager: Orlando Zentella ozentella@zeval.com.mx
############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################



 
{
    'name' : 'Dirección para México',
    'version' : '1.0',
    'author' : 'Zenpar',
    'website' : 'http://www.zeval.com.mx',
    'category' : 'Localization',
    'depends' : ['base', 'account'],
    'description': """
Añade los campos no. exterior y no. interior, y también los campos colonia, municipio y ciudad, los cuales están ligados
    """,
    'data': [
        # 'data/res_country_state_ciudad.xml',
        # 'data/res_country_state_municipio.xml',
        # 'data/res_country_state_municipio_colonia.xml',
        'views/partner_view.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'images': [],
}
