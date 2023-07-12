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
        item.list_price = vals["test_charge"]
        item.name = vals["name"]
        return super(Services, self).write(vals)
