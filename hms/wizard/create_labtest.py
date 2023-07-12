from odoo import fields, api, models, _
from odoo.exceptions import UserError
import calendar
import time
import datetime

class Labtestwizard(models.TransientModel):
    _name = 'create.lab.test.wizard'

    request = fields.Many2one("hms.labtest.request", string="Request Name", readonly=True)
    tests = fields.Many2many("hms.labtest" , "request_testtyps" , "test_id" , "request" , string="Lab Tests")

    def create_tests(self):
        lab_test = self.env["hms.many.testtypes"]
       
        test_id = self.request.id

        if test_id:
            for test in self.tests:
               
                list_value = {
                    'lab_department': test.department.id,
                    'test': test_id,
                    'test_type': test.id,   
                }
                test = lab_test.create(list_value)
                test.onchange_test_type_id()
       