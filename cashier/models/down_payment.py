from odoo import fields, api, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class DownPayment(models.Model):

    _inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
    _name = 'cashier.downpayment'
    _order = "name desc"

    def _get_user(self):
        return self.env.uid

    def _get_sessoin(self):
        session_obj = self.env['cashier.session']
        domain = [('cashier', '=', self.env.uid),('state','=','in_progress')]
        sessoin_ids = session_obj.search(domain, limit=1)

        return sessoin_ids.id or False
    
    name = fields.Char(string="Payment Number #", readonly=True) #states={'paid': [('readonly', True)]}
    #invoice_id = fields.Many2one('cashier.invoice',string="invoice #")
    partner_id = fields.Many2one('res.partner',string="Partner",required=True,states={'paid': [('readonly', True)]})
    amount = fields.Float(string="Amount",states={'paid': [('readonly', True)]})
    note = fields.Text(sting="Notes")
    payment_account = fields.Many2one('account.journal', domain="[('type', 'in', ('bank', 'cash'))]" , string="Payment Method",required=True,states={'paid': [('readonly', True)]})
    created_time = fields.Datetime(string="Created Time", readonly=True ,default=lambda *a: datetime.now())
    cashier = fields.Many2one('res.users',string="Cashier",default=_get_user,readonly=True)
    account_line = fields.One2many('downpayment.line','down_payment_id' , "Accounts lines",states={'paid': [('readonly', True)]})

    sessoin_id = fields.Many2one('cashier.session',string="session #", readonly=True , default=_get_sessoin)
    state = fields.Selection([('draft','Draft'),('paid','Paid')] , string="State",track_visibility='always',default='draft')
    
    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('cashier.downpayment') or _('New')
            result = super(DownPayment, self).create(vals)
            return result
    
    def register_payment(self):
        sessoin_id = self._get_sessoin()
        if sessoin_id:
            for down_payment in self:
                vals = {
                        # 'invoice_id':self.invoice_id.id,
                        'partner_id':down_payment.partner_id.id,
                        'amount': down_payment.amount,
                        'note':down_payment.note,
                        'payment_account':down_payment.payment_account.id,
                    }
                p = self.env['cashier.payment'].create(vals)
                
                for line in down_payment.account_line:
                    vals = {
                            'payment_id':p.id,
                            'account_id':line.account_id.id,
                            'paid_amount': line.paid_amount
                        }
                    l = self.env['payment.account'].create(vals)

                down_payment.state = "paid"
        else:
            raise Warning(_("please start session first"))

    
class DownPaymentline(models.Model):
    _name = 'downpayment.line'
    _rec_name = "account_id"
    down_payment_id = fields.Many2one('cashier.downpayment',string="down payment #")
    account_id = fields.Many2one('account.account',string="Account",required=True)
    paid_amount = fields.Float(string="Amount",required=True)

        
        
