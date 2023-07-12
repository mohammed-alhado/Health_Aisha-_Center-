from odoo import fields, api, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class Session(models.Model):

    _inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
    _name = 'cashier.session'
    _order = "name desc"

    def _get_user(self):
        return self.env.uid

    STATES = [
            ('in_progress', 'In Progress'),
            ('closed', 'Closed'),
            ('posted','Posted')
        ]

    name = fields.Char(string="Session Number #", readonly=True)
    start_time = fields.Datetime(string="Start Time",default=lambda *a: datetime.now(),readonly=True)
    end_time = fields.Datetime(string="End Time",readonly=True)
    cashier = fields.Many2one('res.users',string="Cashier",default=_get_user,readonly=True)
    payments_line = fields.One2many('cashier.payment','sessoin_id' , "Payments lines")
    session_account = fields.One2many('session.account','sessoin_id', "Accounts lines")
    sessoin_journal = fields.One2many('session.journal','sessoin_id', "Jouranls lines")
    note = fields.Text(sting="Notes")
    state = fields.Selection(STATES, string='State', default=lambda *a: 'in_progress')

    total_in_cash = fields.Float("Cash",compute="_compute_total")
    total_in_bank = fields.Float("Bank",compute="_compute_total")
    total_amount = fields.Float("Total Amount",compute="_compute_total")
    
    def _compute_total(self):
        for payment in self:
            totalcash = 0
            totalbank = 0
            for line in payment.payments_line:
                if line.payment_account.type == 'cash':
                    totalcash += line.amount
                if line.payment_account.type == 'bank':
                    totalbank += line.amount

            payment.total_in_cash = totalcash
            payment.total_in_bank = totalbank
            payment.total_amount = totalcash + totalbank

            
    @api.model
    def create(self, vals):
        session_obj = self.env['cashier.session']
        domain = [('cashier', '=', self.env.uid),('state','=','in_progress')]
        sessoin_ids = session_obj.search(domain, limit=1)
        if sessoin_ids.id:
            raise Warning(_("You have already sessoin"))
        else:
            if vals:
                vals['name'] = self.env['ir.sequence'].next_by_code('cashier.session') or _('New')
                result = super(Session, self).create(vals)
                return result
    
    def close_session(self):
        payment_ids = ",".join(str(payment.id) for payment in self.payments_line)
        
        query = """SELECT DISTINCT account_id FROM payment_account where payment_id in ("""+ payment_ids + """)"""
        self.env.cr.execute(query)
        vals = self.env.cr.fetchall()
        
        if vals:
            for va in vals:
                
                self.env.cr.execute("""SELECT paid_amount FROM payment_account where account_id = """+str(va[0])+""" and payment_id in ("""+ payment_ids + """)""")
                acc = self.env.cr.fetchall()
                total_in_account = 0
                if acc:
                    for amount in acc:
                        total_in_account += amount[0]

                account_total = {
                        'account_id': va[0] ,
                        'total': total_in_account,
                        'sessoin_id': self.id
                    }
                line_ids = self.env['session.account'].create(account_total)

        query = """SELECT DISTINCT payment_account FROM cashier_payment  where sessoin_id = """ + str(self.id)
        self.env.cr.execute(query)
        vals = self.env.cr.fetchall()
        
        if vals:
            for va in vals:
                
                self.env.cr.execute("""SELECT amount FROM cashier_payment where payment_account = """+str(va[0])+""" and sessoin_id = """+ str(self.id) )
                acc = self.env.cr.fetchall()
                total_in_journal = 0
                if acc:
                    for amount in acc:
                        total_in_journal += amount[0]

                journal_total = {
                        'journal_id': va[0] ,
                        'total': total_in_journal,
                        'sessoin_id': self.id
                    }
                line_ids = self.env['session.journal'].create(journal_total)
            self.state = 'closed'
    def post_session(self):
        invoice_obj = self.env["account.move"]
        inv_ids = []
        curr_invoice = {
            # 'partner_id': self.partner_id.id,
            'journal_id': self.env['account.journal'].search([('code','=','MISC')],limit=1).id,
            'state': 'draft',
            'type':'entry',
            'date': datetime.now(),
            'ref': "ايراد يوم" + str(datetime.now()) ,
           
        }
        inv_ids = invoice_obj.create(curr_invoice)
        inv_id = inv_ids.id

        if inv_ids:
            list_value = []
            for journal in self.sessoin_journal:
                prd_account_id = journal.journal_id.default_credit_account_id.id
                list_value.append((0,0, {
                    'account_id': prd_account_id,
                    # 'partner_id': self.partner_id.id,
                    'debit': journal.total,
                }))


            for account in self.session_account:
                list_value.append((0,0, {
                    'account_id': account.account_id.id,
                    # 'partner_id': self.partner_id.id,
                    'credit': account.total,
                }))
            
            inv_ids.write({'line_ids': list_value})

        

        inv_ids.action_post()
            # self.session_account= account_total
        self.end_time = datetime.now()
        self.state = 'posted'

class AccountsLines(models.Model):
    _name = 'session.account'
    sessoin_id = fields.Many2one('cashier.session',string="session #")

    account_id = fields.Many2one("account.account",string="Account")
    total = fields.Float("Total")

class JournalsLines(models.Model):
    _name = 'session.journal'
    sessoin_id = fields.Many2one('cashier.session',string="session #")

    journal_id = fields.Many2one("account.journal",string="Journal")
    total = fields.Float("Total")
        
        
