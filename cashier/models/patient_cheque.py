from odoo import fields, api, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class Cheque(models.Model):

    _inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
    _name = 'cashier.cheque'
    _order = "id desc"

    def _get_user(self):
        return self.env.uid


    invoice_id = fields.Many2one("cashier.invoice",string="Invoice number",readonly=True)
    name = fields.Char("Cheque number",required=True)
    partner_id = fields.Many2one("res.partner",string="patient")
    bank_holder = fields.Many2one('account.journal', domain="[('type', '=', 'bank')]" , string="Bank holder",required=True)
    cheque_date = fields.Date("Effected Date",required=True)
    cheque_bank = fields.Char("Bank of Cheque")
    amount = fields.Float("Amount",required=True)
    cashier = fields.Many2one("res.users",string="Cashier",default=_get_user,readonly=True)
    note = fields.Text("Notes")
    cheque_bank = fields.Char("Bank of Cheque")
    amount_due = fields.Float("Amount Due")

    cheque_state = fields.Selection([('waiting','In Waiting'),('paid','Paid'),('rejected','Rejected')] , string="State",track_visibility='always',default='waiting')
    account_line = fields.One2many('cheque.account','cheque_id' , "Accounts lines")
    
    def register_payment(self):
        for cheque in self:
            cheque.invoice_id.paid_amount += cheque.amount
            cheque.invoice_id.change_due_amount()
            vals = {
                    'invoice_id':cheque.invoice_id.id,
                    'partner_id':cheque.partner_id.id,
                    'amount': cheque.amount,
                    'note':cheque.note,
                    'payment_account':cheque.bank_holder.id,
                }
            p = self.env['cashier.payment'].create(vals)
            for line in cheque.account_line:
                vals = {
                        'payment_id':p.id,
                        'account_id':line.account_id.id,
                        'paid_amount': line.amount
                    }
                l = self.env['payment.account'].create(vals)

                invoice_line = self.env['invoice.line'].search([('invoice_id', '=', cheque.invoice_id.id),('account_id','=',line.account_id.id)],limit=1)
                if invoice_line.subtotal <= cheque.amount:
                    invoice_line.paid_amount += invoice_line.subtotal
                else:
                    invoice_line.paid_amount += cheque.amount
                # line.paid_amount += line.subtotal - line.paid_amount
            cheque.cheque_state = "paid"
class ChequeAccount(models.Model):
    _name = 'cheque.account'
    _rec_name = "account_id"
    cheque_id = fields.Many2one('cashier.cheque',string="payment #")
    account_id = fields.Many2one('account.account',string="Account" , readonly=True)
    amount = fields.Float(string="Amount", readonly=True)

        
        
