# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class Reception(models.Model):
    _name = 'hms.reception'
    _description = 'services reception'
    _order = "request_time desc"

    name = fields.Char(string="#",readonly=True)
    patient = fields.Many2one("hms.patient",string="Patient name",required=True)
    request_time = fields.Datetime(string="Time of Request",default=lambda *a: datetime.now(),readonly=True)

    clinic = fields.Many2one("hms.doctor",string="Clinic")
    clinic_amount = fields.Float("amount",readonly=True)
    image = fields.Many2one("hms.image",string="imaging")
    image_amount = fields.Float("amount",readonly=True)
    
    surgery_service = fields.Many2one("hms.surgery",string="Surgery")
    surgery_amount = fields.Float("surgery amount",readonly=True)

    dental = fields.Many2many("hms.dental","request_dental","dental_id","request_id",string="dental")
    dental_amount = fields.Float("amount",readonly=True)

    lab = fields.Many2many("hms.labtest","request_lab","lab_id","request_id",string="lab")
    lab_amount = fields.Float("amount",readonly=True) 
    subtotal = fields.Float("sum")

    def change_subtotal(self):
        for request in self:
            request.subtotal = 0
            request.subtotal = request.clinic_amount+request.image_amount+request.surgery_amount+request.dental_amount+request.lab_amount
    
    @api.onchange("clinic")
    def onchange_clinic(self):
        for request in self:
            request.clinic_amount = request.clinic.fees
            request.change_subtotal()

    @api.onchange("image")
    def onchange_image(self):
        for request in self:
            request.image_amount = request.image.fees
            request.change_subtotal()

    @api.onchange("surgery_service")
    def onchange_surgery_service(self):
        for request in self:
            request.surgery_amount = request.surgery_service.fees
            request.change_subtotal()

    @api.onchange("dental")
    def onchange_dental(self):
        for request in self:
            dental_amount = 0
            for dent in request.dental:
                dental_amount += dent.fees
            request.dental_amount =  dental_amount
            request.change_subtotal()

    @api.onchange("lab")
    def onchange_lab(self):
        for request in self:
            lab_amount = 0
            for lab in request.lab:
                lab_amount += lab.test_charge
            request.lab_amount = lab_amount
            request.change_subtotal()

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hms.reception') or _('New')
        return super(Reception, self).create(vals)

    def add_serivce(self):
        for request in self:
            wizard_form = self.env.ref('reception.view_create_service_wizard', False)
            wizard_model = self.env['create.service.wizard']
            vals = {
                    'request':request.id,
                    }
            new = self.env['create.service.wizard'].create(vals)
            return {
                'name':"Services",
                'type': 'ir.actions.act_window',
                'res_model': 'create.service.wizard',
                'res_id': new.id,
                'view_id':  self.env.ref('reception.view_create_service_wizard',False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
                }

class Patient(models.Model):

    _name = "hms.patient"
    _description = "patients records"

    name = fields.Char("name")
    phone = fields.Char("phone")
    age = fields.Char("age")
    address = fields.Char("address")

class Doctor(models.Model):

    _name = "hms.doctor"
    _description = "Doctors records"

    name = fields.Char("name")
    fees = fields.Float("Fees")


class Image(models.Model):

    _name = "hms.image"
    _description = "images records"

    name = fields.Char("name")
    fees = fields.Float("Fees")

class Surgery(models.Model):

    _name = "hms.surgery"
    _description = "surgery records"

    name = fields.Char("name")
    fees = fields.Float("Fees")

class Dental(models.Model):

    _name = "hms.dental"
    _description = "dental records"

    name = fields.Char("name")
    fees = fields.Float("Fees")