from odoo import fields, api, models, _
from odoo.exceptions import UserError
import datetime
from dateutil import relativedelta


class RefundWizard(models.TransientModel):
    _name = 'refund.wizard'

    def get_default_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        return journal.id

    invoice_id = fields.Many2one("cashier.invoice", string="Invoice", readonly=True)
    partner_id = fields.Char("patient")#fields.Many2one('res.partner',string="Partner" , readonly=True)
    amount = fields.Float(string="Amount")
    note = fields.Char(sting="Notes")
    payment_account = fields.Many2one('account.journal', domain="[('type', '=', 'cash')]",required=True, default=get_default_journal , string="Payment Method")

    
    def validate_payment(self):
        for payment in self:
            payment.invoice_id.paid_amount += -payment.amount
            payment.invoice_id.change_due_amount()
            # account = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
            vals = {
                'invoice_id':payment.invoice_id.id,
                'partner_id':payment.partner_id,#.id,
                'amount': -payment.amount,
                'note':payment.note,
                'payment_account':payment.payment_account.id,
            }
            p = self.env['cashier.payment'].create(vals)
            
            for line in payment.invoice_id.invoice_line:
                vals = {
                        'payment_id':p.id,
                        'account_id':line.account_id.id,
                        'paid_amount': -line.paid_amount
                }
                l = self.env['payment.account'].create(vals)

                line.paid_amount += -line.paid_amount

            payment.invoice_id.invoice_state = "refunded"