# -*- coding: utf-8 -*-

from odoo import models, fields, api, _ 
from odoo.exceptions import UserError, Warning
import datetime

class Request(models.Model):
    _inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
    _name = "material.request"
    _order = "name desc"

    def _get_user(self):
        return self.env.uid

    name = fields.Char(string="name")
    department = fields.Many2one("department.department",string="request from " , required=True)
    department_id = fields.Selection([("lab","Lab Department"), ("ultrasound", "Ultrasound Department"),("x_ray", "X-RAY Department"), ("ct", "CT Department")], string="Cost Center department")
    requester = fields.Many2one("res.users",string="Requester",default=_get_user,readonly=True)
    request_type = fields.Selection([("purchase","Purchase"),("inventory","Inventory")],string="Request Type",required=True)
    material_line = fields.One2many("material.line","request_id",string="Material Lines")
    note = fields.Text(string="Notes")
    state = fields.Selection([("draft","Draft"),("rejected","Rejected"),("approved","Approved"),("done","Done")],default="draft",string="State")

    @api.model
    def create(self,vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('material.request') or _('New')
            result = super(Request, self).create(vals)
            return result
    def unlink(self):
        for material in self:
            if material.state not in ('draft'):
                raise Warning(_("cannot be deleted request it is not in draft"))
        return models.Model.unlink(self)


    def set_done(self):
        self.state = "done"
        if self.request_type == "inventory":
            amount = 0
            for line in self.material_line:
                amount += line.item_id.standard_price * line.qty
            vals = {
                "service_ref":self.name,
                "amount":amount,
                "date":datetime.date.today(),
                "department_id":self.department_id,
            }
            expense_obj = self.env["service.expense"].create(vals)
    def set_approve(self):
        self.state = "approved"
    def set_reject(self):
        self.state = "rejected"
        
class Department(models.Model):
    _name = "department.department"
    _order = "name desc"

    name = fields.Char(string="name")

class MaterialLine(models.Model):
    _name = "material.line"

    request_id = fields.Many2one("material.request","request id")
    item_id = fields.Many2one("product.product",string="Item")
    qty = fields.Float("Quantity")
    uom = fields.Many2one("uom.uom",string="UOM")