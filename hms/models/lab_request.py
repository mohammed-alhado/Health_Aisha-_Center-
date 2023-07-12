from odoo import models, fields, api , _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class LabtestRequest(models.Model):
    _name = 'hms.labtest.request'
    _description = 'Labt test Request'

    _order = "request_time desc"

    name = fields.Char("Request #" , readonly=True)
    patient = fields.Char("Patient name" , required=True)
    phone = fields.Char("Phone")
    age = fields.Char("Age")
    invoice_id = fields.Many2one("cashier.invoice" , readonly=True)
    # invoice_state = fields.Selection(related="invoice_id.invoice_state")
    payment_state = fields.Selection([('draft','Draft'),('in_payment','In Payment'),('paid','Paid'),('refunded','Refunded')],string="Invoice state")
    lab_test = fields.One2many("hms.many.testtypes","test", string="List of tests",ondelete='cascade')
    request_time = fields.Datetime(string="Time of Request",default=lambda *a: datetime.now(),readonly=True)
    date_analysis = fields.Datetime(string="Analysis Date:",readonly=True)
    state = fields.Selection([("draft","Draft"),("invoiced","Invoiced"),("completed","Completed")],default="draft",string="State")
    total_amount = fields.Float(string='Paid Amount',readonly=True)
    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('hms.labtest.request') or _('New')
            result = super(LabtestRequest, self).create(vals)
            return result

    def action_lab_invoice_create(self):
        invoice_obj = self.env['cashier.invoice']
        vals = {
            'patient':self.patient,
            'note':self.name + " " 
        }
        inv_ids = invoice_obj.create(vals)
        for test_line in self.lab_test:
            invoice_line = []
            item = self.env['product.template'].search([("name","=",test_line.test_type.name)]) 
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
        self.invoice_id = inv_ids.id
        total = 0
        for test in self.lab_test:
                total += test.test_price
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
        self.state = "completed"

    def print_lab_report(self):
        if self.payment_state == "paid":
            return self.env.ref('hms.labtest_report').report_action(self)
        else :
            raise Warning(_("Charge of request was not paid"))
    def select_tests(self):
        wizard_form = self.env.ref('hms.view_create_labtest_wizard', False)
        wizard_model = self.env['create.lab.test.wizard']
        vals = {
                'request':self.id,
                }
        new = wizard_model.create(vals)
        return {
            'name':"Lab Tests",
            'type': 'ir.actions.act_window',
            'res_model': 'create.lab.test.wizard',
            'res_id': new.id,
            'view_id':  self.env.ref('hms.view_create_labtest_wizard',False).id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
            }
class TestTypes(models.Model):
    _name = "hms.many.testtypes"

    lab_department = fields.Many2one('hms.lab.department', string='Department', readonly=True)
    test = fields.Many2one('hms.labtest.request')
    test_type = fields.Many2one('hms.labtest', string='Test Type', domain="[('is_available', '=', True)]", required=True, help="Lab test type")
    test_price = fields.Float(related='test_type.test_charge')
    no_sample = fields.Char("Sample code" , default=lambda self: self._get_lab_name())
    note = fields.Char("Notes")
    lab_test_criteria = fields.One2many('hms.lab.resultcriteria', 'testtypes_id', string='Lab Test Result')
    @api.model
    def _get_lab_name(self):
        return self.test.name
    

    @api.onchange('test_type')
    def onchange_test_type_id(self):
        self.lab_department = self.test_type.department
        lab_test_criteria = []
        if self.test_type and self.test_type.criteria_line:
            self.lab_test_criteria = False
            for criteria in self.test_type.criteria_line:
                lab_test_criteria.append((0, 0, {
                    'name': criteria.name,
                    'result':criteria.default_result,
                    'normal_range': criteria.normal_range,
                    'units': criteria.units and criteria.units.id or False,
                    'sequence': criteria.sequence,
                }))
            self.lab_test_criteria = lab_test_criteria
        else:
            self.lab_test_criteria = False
    
class LabResultCriteria(models.Model):
    _name= 'hms.lab.resultcriteria'
    _description = 'Lab Test Result Criteria'
    _order="sequence"

    name = fields.Char(string='Tests', size=128, required=True)
    result_chooses = fields.Many2one("criteria.result.choose",string="Chooses")
    result = fields.Text(string='Result')
    normal_range = fields.Text(string='Normal Range')
    units = fields.Many2one('hms.lab.unit', string='Units')
    sequence = fields.Integer(string='Sequence')
    testtypes_id = fields.Many2one('hms.many.testtypes', string='Lab Tests')

    @api.onchange('result_chooses')
    def change_result(self):
        self.result = self.result_chooses.name