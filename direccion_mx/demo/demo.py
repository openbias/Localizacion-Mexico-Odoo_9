import logging
import sys
import csv
from lxml import etree as ET
import xlrd

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', )

class csv_to_xml_odoo:

    def __init__(self, path='', model=''):
        self.path = path
        self.model = model
        self.data_dict = {}

    def search_data_csv_list(self, path_to_csv=None):
        self.path = path_to_csv if path_to_csv != None else self.path
        ifile  = open(self.path)
        reader = csv.reader(ifile, delimiter=';', quotechar='"')
        data_dict = {}
        rownum = 0
        product_name = False
        for row in reader:
            # Save header row.
            if rownum == 0:
                header = row
            else:
                data_line = {}
                colnum = 0
                #print 'col', row
                for col in row:
                    data_line[header[colnum]] = col
                    colnum += 1
                if product_name != row[0]:
                    product_name = row[0]
                    data_dict[row[0]] = []
                data_dict[row[0]].append(data_line)
            rownum += 1 
        ifile.close()
        return data_dict

    def compute_field(self, data, records):
        m_id = records.get('id', '')
        m_model = records.get('model', '')
        record = ET.SubElement(data, "record", {
                'id': m_id,
                'model': m_model
            })
        for r in records:
            if r in ['id', 'model']:
                continue
            name = r.split('/') or r.split('.')
            if len(name) > 1:
                field = ET.SubElement(record, "field", {'name': name[0], 'ref':records[r].decode('utf-8') })
            else:
                field = ET.SubElement(record, "field", {'name': r})
                field.text = records[r].decode('utf-8')

    def process_xml(self):
        dict_fields = self.search_data_csv_list(self.path)
        openerp = ET.Element("openerp")
        data = ET.SubElement(openerp, "data", {'noupdate': '1'})
        for l in dict_fields:
            record = dict_fields[l][0]    
            record['model'] = self.model
            self.compute_field(data, record)
        return openerp

    def write_xml(self):
        xml_name = self.model.replace('.', '_')
        openerp = self.process_xml()
        output_file = open( '/tmp/%s.xml'%(xml_name), 'w' )
        output_file.write( '<?xml version="1.0" encoding="utf-8"?>' )
        output_file.write( ET.tostring(openerp, encoding="utf-8", pretty_print=True) )
        output_file.close()
        return

path = "res.country.state.municipio.csv"
model = 'res.country.state.municipio.colonia'
xml = csv_to_xml_odoo(path=path, model=model)
p = xml.write_xml()