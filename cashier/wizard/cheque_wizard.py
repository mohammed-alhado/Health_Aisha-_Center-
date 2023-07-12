from odoo import fields, api, models, _
from odoo.exceptions import UserError

class ChequeWizard(models.TransientModel):
    _name = 'cheque.wizard'

    invoice_id = fields.Many2one("cashier.invoice", string="Invoice", readonly=True)
    cheque_number = fields.Char("Cheque number")
    bank_holder = fields.Many2one('account.journal', domain="[('type', '=', 'bank')]" , string="Bank holder")    
    amount = fields.Float(string="Amount")
    effected_date = fields.Date("Effected Date")
    cheque_bank = fields.Char("Bank of Cheque")
    note = fields.Char(sting="Notes")

    amount_due = fields.Float(string="Amount Due" , readonly=True)
    line_account = fields.Many2one('invoice.line', domain="[('invoice_id' , '=' , invoice_id)]") #,('paid_amount','<','200')

    def register_cheque(self):
        for cheque in self:
            if cheque.amount < cheque.amount_due:
                if cheque.line_account == False:
                    raise Warning(_("please select account"))
                else:
                    # session_obj = self.env['cashier.session']
                    # domain = [('cashier', '=', self.env.uid),('state','=','in_progress')]
                    # sessoin_ids = session_obj.search(domain, limit=1)
                    cheque_model = self.env['cashier.cheque']
                    vals = {
                            'invoice_id':cheque.invoice_id.id,
                            'name':cheque.cheque_number,
                            'bank_holder':cheque.bank_holder.id,
                            'amount':cheque.amount,
                            'cheque_date':cheque.effected_date,
                            'cheque_bank':cheque.cheque_bank,
                            'note':cheque.note
                            }
                    cheque_id = cheque_model.create(vals)
                    for line in cheque.line_account:
                        vals = {
                                'cheque_id':cheque_id.id,
                                'account_id':line.account_id.id,
                                'amount': cheque_id.amount
                            }
                        l = self.env['cheque.account'].create(vals)

            elif cheque.amount == cheque.amount_due:
                cheque_model = self.env['cashier.cheque']
                vals = {
                        'invoice_id':cheque.invoice_id.id,
                        'name':cheque.cheque_number,
                        'bank_holder':cheque.bank_holder.id,
                        'amount':cheque.amount,
                        'cheque_date':cheque.effected_date,
                        'cheque_bank':cheque.cheque_bank,
                        'note':cheque.note
                        }
                cheque_id = cheque_model.create(vals)
                for line in cheque_id.invoice_id.invoice_line:
                    vals = {
                            'cheque_id':cheque_id.id,
                            'account_id':line.account_id.id,
                            'amount': line.subtotal - line.paid_amount
                        }
                    l = self.env['cheque.account'].create(vals)

