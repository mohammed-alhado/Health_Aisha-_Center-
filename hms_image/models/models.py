# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Image(models.Model):
    _name = 'hms.image'
    _description = 'data of doctor'

    name = fields.Char(string="Test Name",required=True)
    fees = fields.Float(string='Fees',required=True)
    department = fields.Many2one("hms.image.department","Department",required=True)
    doctor_dues = fields.Float(string="Doctor Dues")
    comment = fields.Text(string="Comment")

    @api.model
    def create(self, vals):
        result =  super(Image, self).create(vals)
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
        return super(Image, self).write(vals)

class ImageDepartment(models.Model):
    _name = "hms.image.department"
    _description = "Imaging Department"

    name = fields.Char("Name of department",required=True)
