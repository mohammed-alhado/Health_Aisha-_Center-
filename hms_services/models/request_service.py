# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta


class RequestService(models.Model):
    _name = 'request.services'
    _description = 'request medical services'
    _order = "request_time desc"

    name = fields.Char(string="Request #", readonly=True)
    patient = fields.Char("Patient" , required=True)
    # patient = fields.Many2one('oeh.medical.patient',string="Patient")
    service_line = fields.One2many("service.line","name",string="service lines")

    # doctor = fields.Many2one("oeh.medical.physician",string="Doctor")
    move_id = fields.Many2one("cashier.invoice","invoice #",readonly=True)
    request_time = fields.Datetime(string="Time of Request",default=lambda *a: datetime.now(),readonly=True)
    state = fields.Selection([("draft","Draft"),("invoiced","Invoiced")],default="draft",string="State")
    invoice_state = fields.Selection(related="move_id.invoice_state")
    total_amount = fields.Float(string='Paid Amount',readonly=True)
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('request.services') or _('New')
        return super(RequestService, self).create(vals)

    def create_invoice(self):
        invoice_obj = self.env['cashier.invoice']
        vals = {
            'patient':self.patient,#.id,
            'note':self.name 
        }
        inv_ids = invoice_obj.create(vals)
        for service_line in self.service_line:
            invoice_line = []
            item = self.env['product.template'].search([("name","=",service_line.service.name)],limit=1) 
            item.list_price = service_line.price
            item_id = item.id

            invoice_line_obj = self.env['invoice.line']
            invoice_line = {
                'item_id': item_id,
                'qty': 1,
                'invoice_id': inv_ids.id
            }
            line_ids = invoice_line_obj.create(invoice_line)
            line_ids.onchange_item()
            line_ids.compute_subtotal()

        inv_ids._compute_amount()
        inv_ids.change_due_amount()
        self.move_id = inv_ids.id

        total = 0
        for service in self.service_line:
                total += service.price
        self.total_amount = total
        
        self.state = "invoiced"
        view_id = self.env.ref('cashier.cashier_invoice_form').id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cashier.invoice',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'name': _('invoice'),
            'res_id': inv_ids.id
        }

    def set_to_completed(self):
        if self.move_id.invoice_state == "paid":
            
            # service = self.env["product.template"].search([("name","ilike",self.service.name)])
            # if service.property_account_expense_id:
            #     account_id = service.property_account_expense_id.id
            # else:
            #     account_id = service.categ_id.property_account_expense_categ_id.id
            # doctor_amount = self.service.doctor_dues
            # dues_obj = self.env['dues.dues']
            # vals = {
            #     'name':self.doctor.id,
            #     'ref':self.name,
            #     'per_type':'other',
            #     'amount':doctor_amount,
            #     'account_id':account_id
            # }
            # dues_ids = dues_obj.create(vals)

            self.write({'state': 'completed'})


class ServiceLines(models.Model):
    _name = 'service.line'
    _description = 'medical services lines'

    name = fields.Many2one("request.services",string="Medical Service Request")
    service = fields.Many2one("services.services")
    price = fields.Float("Fees")

    @api.onchange('service')
    def onchange_service(self):
        self.price = self.service.fees