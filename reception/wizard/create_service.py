from odoo import fields, api, models, _
from odoo.exceptions import UserError, Warning
import calendar
import time
import datetime

class Servicewizard(models.TransientModel):
    _name = 'create.service.wizard'

    
    request = fields.Many2one("hms.reception", string="Request Name", readonly=True)
    patient = fields.Many2one(related="request.patient")
    clinic = fields.Many2one("hms.doctor",string="Clinic")
    clinic_amount = fields.Float("clinic amount")
    image = fields.Many2one("hms.image",string="imaging")
    image_amount = fields.Float("imaging amount")
    
    surgery_service = fields.Many2one("hms.surgery",string="Surgery")
    surgery_amount = fields.Float("surgery amount")

    dental = fields.Many2many("hms.dental","hms_request_dental","dental_id","request_id",string="dental")
    dental_amount = fields.Float("dental amount")

    lab = fields.Many2many("hms.labtest","hms_request_lab","lab_id","request_id",string="lab")
    lab_amount = fields.Float("amount") 

    @api.onchange("clinic")
    def onchange_clinic(self):
        for request in self:
            request.clinic_amount = request.clinic.fees

    @api.onchange("image")
    def onchange_image(self):
        for request in self:
            request.image_amount = request.image.fees

    @api.onchange("surgery_service")
    def onchange_surgery_service(self):
        for request in self:
            request.surgery_amount = request.surgery_service.fees

    @api.onchange("dental")
    def onchange_dental(self):
        for request in self:
            request.dental_amount = request.dental.fees

    @api.onchange("lab")
    def onchange_lab(self):
         for request in self:
            lab_amount = 0
            for lab in request.lab:
                lab_amount += lab.test_charge
            request.lab_amount = lab_amount
    
    def create_service(self):

        if self.clinic:
            for service in self.clinic:
                self.request.clinic = service.id
                self.request.clinic_amount = self.clinic_amount
                self.request.change_subtotal()

        if self.image:
            for service in self.image:
                self.request.image = service.id
                self.request.image_amount = self.image_amount
                self.request.change_subtotal()

        if self.surgery_service:
            for service in self.surgery_service:
                self.request.surgery_service = service.id
                self.request.surgery_amount = self.surgery_amount
                self.request.change_subtotal()

        if self.dental:
            for dental in self.dental:
                self.request.write({'dental':[(4,dental.id)]})
            self.request.dental_amount = self.dental_amount
            self.request.change_subtotal()

        if self.lab:
            for lab in self.lab:
                self.request.write({'lab':[(4,lab.id)]})
            self.request.lab_amount = self.lab_amount
            self.request.change_subtotal()
            lab_request_obj = self.env["hms.labtest.request"]
            list_value = {
                        'patient': self.patient.name,
                        'phone': self.patient.phone,
                        'age': self.patient.age,
                        'payment_state': 'paid',
                        'state': 'invoiced',  
                        'total_amount': self.lab_amount,
                    }
            lab_request = lab_request_obj.create(list_value)

            lab_test = self.env["hms.many.testtypes"]
           
            test_id = lab_request.id

            if test_id:
                for test in self.lab:
                   
                    list_value = {
                        'lab_department': test.department.id,
                        'test': test_id,
                        'test_type': test.id,   
                    }
                    test = lab_test.create(list_value)
                    test.onchange_test_type_id()

        if self.clinic or self.image or self.surgery_service or self.dental or self.lab:
            return self.env.ref('reception.action_report_cashier_invoice').report_action(self)
       