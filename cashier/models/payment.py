from odoo import fields, api, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class Payment(models.Model):

    _inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
    _name = 'cashier.payment'
    _order = "name desc"

    def _get_user(self):
        return self.env.uid

    def _get_sessoin(self):
        session_obj = self.env['cashier.session']
        domain = [('cashier', '=', self.env.uid),('state','=','in_progress')]
        sessoin_ids = session_obj.search(domain, limit=1)

        return sessoin_ids.id or False

    name = fields.Char(string="Payment Number #", readonly=True)
    invoice_id = fields.Many2one('cashier.invoice',string="invoice #")
    partner_id = fields.Char("Partner")
    # partner_id = fields.Many2one('res.partner',string="Partner")
    amount = fields.Float(string="Amount")
    note = fields.Text(sting="Notes")
    payment_account = fields.Many2one('account.journal', domain="[('type', 'in', ('bank', 'cash'))]" , string="Payment Method", required=True)
    payment_time = fields.Datetime(string="Payment Time", readonly=True ,default=lambda *a: datetime.now())
    cashier = fields.Many2one('res.users',string="Cashier",default=_get_user,readonly=True)
    account_line = fields.One2many('payment.account','payment_id' , "Accounts lines")

    sessoin_id = fields.Many2one('cashier.session',string="session #", readonly=True , default=_get_sessoin)
    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('cashier.payment') or _('New')
            result = super(Payment, self).create(vals)
            return result
    

class PaymentAccount(models.Model):
    _name = 'payment.account'
    _rec_name = "account_id"
    payment_id = fields.Many2one('cashier.payment',string="payment #")
    account_id = fields.Many2one('account.account',string="Account")
    paid_amount = fields.Float(string="Paid Amount")

        
        
