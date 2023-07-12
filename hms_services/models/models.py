# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Services(models.Model):
    _name = 'services.services'
    _description = 'services.services'

    name = fields.Char(string="Service Name")
    service_type = fields.Selection([('emergency','Emergency'),('nursing','Nursing')], string="Service Type")
    fees = fields.Float(string='Fees')
    doctor_dues = fields.Float(string="Doctor Dues")
    comment = fields.Text(string="Comment")

    @api.model
    def create(self, vals):
        result =  super(Services, self).create(vals)
        service_val = {
            'name': result.name,
            'list_price': result.fees,
            'type':'service'
        }
        self.env["product.template"].create(service_val)
        return result

    def write(self,vals):
        item = self.env["product.template"].search([("name","=",self.name)],limit=1)
        try:
            if vals["name"]:
                item.name = vals["name"]
        except Exception as e:
            print(('Exception (%s).') % e)
        try:
            if vals["fees"]:
                item.list_price = vals["fees"]
        except Exception as e:
            print(('Exception (%s).') % e)
        return super(Services, self).write(vals)