from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class RequestExpense(models.Model):
    _name = 'hms.request.expense'
    _description = 'request expenses'
    _order = "request_time desc"

    name = fields.Char(string="#",readonly=True)
    request_time = fields.Datetime(string="Time of Request",default=lambda *a: datetime.now(),readonly=True)
    expense = fields.Many2one("hms.expense",string="Expense")
    amount = fields.Float("amount")

    @api.onchange("expense")
    def onchange_expense(self):
        for request in self:
            request.amount = request.expense.fees
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hms.request.expense') or _('New')
        return super(RequestExpense, self).create(vals)
    
class Expense(models.Model):

    _name = "hms.expense"
    _description = "expenses records"

    name = fields.Char("name")
    fees = fields.Float("Fees")
