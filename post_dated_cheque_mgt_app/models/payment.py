# -*- coding: utf-8 -*-

import math
from datetime import date, datetime
from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_invoice_pdc_register_payment(self):
        return self.env['pdc.account.payment']\
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
            .action_register_payment()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    payment_pdc_id = fields.Many2one('pdc.account.payment', string="Originator PDC Payment", help="Payment that created this entry", copy=False)


class PdcAccountPayment(models.Model):
    _name = "pdc.account.payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Payments"
    _order = "payment_date desc, name desc"


    name = fields.Char(readonly=True, copy=False)  # The name is attributed upon post()
    payment_reference = fields.Char(copy=False, readonly=True, help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    move_name = fields.Char(string='Journal Entry Name', readonly=True,
        default=False, copy=False,
        help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', readonly=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]", readonly=True, states={'draft': [('readonly', False)]})

    invoice_ids = fields.Many2many('account.move', help="""Technical field containing the invoices for which the payment has been generated.This does not especially correspond to the invoices reconciled with the payment,as it can have been generated first, and reconciled later""")
    reconciled_invoice_ids = fields.Many2many('account.move', string='Reconciled Invoices', compute='_compute_reconciled_invoice_ids', help="Invoices whose journal items have been reconciled with these payments.")
    has_invoices = fields.Boolean(compute="_compute_reconciled_invoice_ids", help="Technical field used for usability purposes")
    reconciled_invoices_count = fields.Integer(compute="_compute_reconciled_invoice_ids")

    move_line_ids = fields.One2many('account.move.line', 'payment_pdc_id', readonly=True, copy=False, ondelete='restrict')
    move_reconciled = fields.Boolean(compute="_get_move_reconciled", readonly=True)

    state = fields.Selection([('draft', 'Draft'),
                            ('collect_cash','Collect Cash'),
                            ('deposited', 'Deposited'),
                            ('bounced', 'Bounced'),
                            ('posted', 'Posted'),
                            ('returned', 'Returned'),
                            ('cancelled', 'Cancelled'),
                            ], readonly=True, default='draft', copy=False, string="Status")
    
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Internal Transfer')], string='Payment Type', required=True, readonly=True, states={'draft': [('readonly', False)]})
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method', required=True, readonly=True, states={'draft': [('readonly', False)]},
        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"\
        "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n"\
        "Check: Pay bill by check and print it from Odoo.\n"\
        "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n"\
        "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    payment_method_code = fields.Char(related='payment_method_id.code',
        help="Technical field used to adapt the interface to the payment type selected.", readonly=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True, readonly=True, states={'draft': [('readonly', False)]}, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    amount = fields.Monetary(string='Amount', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, tracking=True)
    communication = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True, domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)

    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
                                         help="Technical field used to hide the payment method if the "
                                         "selected journal has only one available which is 'manual'")

    payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True)
    payment_difference_handling = fields.Selection([('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')], default='open', string="Payment Difference Handling", copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", copy=False)
    writeoff_label = fields.Char(
        string='Journal Item Label',
        help='Change label of the counterpart that will hold the payment difference',
        default='Write-Off')
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account", readonly=True, states={'draft': [('readonly', False)]}, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    show_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be displayed or not in the payments form views')
    require_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be required or not in the payments form views')
    bank = fields.Char(string='Bank')
    agent = fields.Char(string='Agent')
    cheque_reference = fields.Char(string='Cheque Reference')
    due_date = fields.Date(string='Due Date', required=True, copy=False)
    account_move_id = fields.Many2one('account.move', string="Move Reference")
    pdc_account_id = fields.Many2one('account.account',string="PDC Receivable Account")
    pdc_account_creditors_id = fields.Many2one('account.account',string="PDC Payable Account")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')


    def _compute_attachment_number(self):
        Attachment = self.env['ir.attachment']
        for payment in self:
            payment.attachment_number = Attachment.search_count([
                ('res_model', '=', 'pdc.account.payment'), ('res_id', '=', payment.id),
            ])

    def action_get_attachment_view(self):
        return True
    
    def button_journal_items(self):
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': ['|','|',('move_id.ref', '=', self.communication),
                            ('move_id.name', '=', self.communication),
                        ('payment_pdc_id', 'in', self.ids)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }

    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': ['|',('name', '=', self.communication), ('ref', '=', self.communication)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }



    @api.onchange('due_date')
    def check_pdc_account(self):
        if self.due_date:
            pdc_account_id = self.company_id.pdc_account_id
            if not pdc_account_id:
                raise UserError(_("Please configure Pdc Payment Account(100501) first, from Invoicing or Accounting setting."))
            pdc_account_creditors_id = self.company_id.pdc_account_creditors_id
            if not pdc_account_creditors_id:
                raise UserError(_("Please configure Pdc Payment Account(100502) first, from Invoicing or Accounting setting."))
            if self.due_date < fields.Date.today():
                raise UserError(_("Please select valid due date...!"))


    @api.model
    def default_get(self, default_fields):
        rec = super(PdcAccountPayment, self).default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids).filtered(lambda move: move.is_invoice(include_receipts=True))

        # Check all invoices are open
        if not invoices or any(invoice.state != 'posted' for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices"))
        # Check if, in batch payments, there are not negative invoices and positive invoices
        dtype = invoices[0].type
        for inv in invoices[1:]:
            if inv.type != dtype:
                if ((dtype == 'in_refund' and inv.type == 'in_invoice') or
                        (dtype == 'in_invoice' and inv.type == 'in_refund')):
                    raise UserError(_("You cannot register payments for vendor bills and supplier refunds at the same time."))
                if ((dtype == 'out_refund' and inv.type == 'out_invoice') or
                        (dtype == 'out_invoice' and inv.type == 'out_refund')):
                    raise UserError(_("You cannot register payments for customer invoices and credit notes at the same time."))

        amount = self._compute_payment_amount(invoices, invoices[0].currency_id, invoices[0].journal_id, rec.get('payment_date') or fields.Date.today())
        rec.update({
            'currency_id': invoices[0].currency_id.id,
            'amount': abs(amount),
            'payment_type': 'inbound' if amount > 0 else 'outbound',
            'partner_id': invoices[0].commercial_partner_id.id,
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
            'communication': invoices[0].invoice_payment_ref or invoices[0].ref or invoices[0].name,
            'invoice_ids': [(6, 0, invoices.ids)],
        })
        return rec

    @api.constrains('amount')
    def _check_amount(self):
        for payment in self:
            if payment.amount < 0:
                raise ValidationError(_('The payment amount cannot be negative.'))

    @api.model
    def _get_method_codes_using_bank_account(self):
        return []

    @api.model
    def _get_method_codes_needing_bank_account(self):
        return []

    @api.depends('payment_method_code')
    def _compute_show_partner_bank(self):
        """ Computes if the destination bank account must be displayed in the payment form view. By default, it
        won't be displayed but some modules might change that, depending on the payment type."""
        for payment in self:
            payment.show_partner_bank_account = payment.payment_method_code in self._get_method_codes_using_bank_account()
            payment.require_partner_bank_account = payment.state == 'draft' and payment.payment_method_code in self._get_method_codes_needing_bank_account()

    @api.depends('payment_type', 'journal_id')
    def _compute_hide_payment_method(self):
        for payment in self:
            if not payment.journal_id or payment.journal_id.type not in ['bank', 'cash']:
                payment.hide_payment_method = True
                continue
            journal_payment_methods = payment.payment_type == 'inbound'\
                and payment.journal_id.inbound_payment_method_ids\
                or payment.journal_id.outbound_payment_method_ids
            payment.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[0].code == 'manual'

    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'payment_type')
    def _compute_payment_difference(self):
        draft_payments = self.filtered(lambda p: p.invoice_ids and p.state == 'draft')
        for pay in draft_payments:
            payment_amount = -pay.amount if pay.payment_type == 'outbound' else pay.amount
            pay.payment_difference = pay._compute_payment_amount(pay.invoice_ids, pay.currency_id, pay.journal_id, pay.payment_date) - payment_amount
        (self - draft_payments).payment_difference = 0

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            if self.journal_id.currency_id:
                self.currency_id = self.journal_id.currency_id

            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            payment_methods_list = payment_methods.ids

            default_payment_method_id = self.env.context.get('default_payment_method_id')
            if default_payment_method_id:
                # Ensure the domain will accept the provided default value
                payment_methods_list.append(default_payment_method_id)
            else:
                self.payment_method_id = payment_methods and payment_methods[0] or False

            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'

            domain = {'payment_method_id': [('payment_type', '=', payment_type), ('id', 'in', payment_methods_list)]}

            if self.env.context.get('active_model') == 'account.move':
                active_ids = self._context.get('active_ids')
                invoices = self.env['account.move'].browse(active_ids)
                self.amount = abs(self._compute_payment_amount(invoices, self.currency_id, self.journal_id, self.payment_date))

            return {'domain': domain}
        return {}

    def action_invoice_cancel(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                if move.state != 'draft':
                    move.button_cancel()
                move.unlink()
            rec.write({
                'state': 'cancelled',
                'move_name': '',
            })

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.invoice_ids and self.invoice_ids[0].invoice_partner_bank_id:
            self.partner_bank_account_id = self.invoice_ids[0].invoice_partner_bank_id
        elif self.partner_id != self.partner_bank_account_id.partner_id:
            # This condition ensures we use the default value provided into
            # context for partner_bank_account_id properly when provided with a
            # default partner_id. Without it, the onchange recomputes the bank account
            # uselessly and might assign a different value to it.
            if self.partner_id and len(self.partner_id.bank_ids) > 0:
                self.partner_bank_account_id = self.partner_id.bank_ids[0]
            elif self.partner_id and len(self.partner_id.commercial_partner_id.bank_ids) > 0:
                self.partner_bank_account_id = self.partner_id.commercial_partner_id.bank_ids[0]
            else:
                self.partner_bank_account_id = False
        return {'domain': {'partner_bank_account_id': [('partner_id', 'in', [self.partner_id.id, self.partner_id.commercial_partner_id.id])]}}

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids and not self.partner_type:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        elif self.payment_type not in ('inbound', 'outbound'):
            self.partner_type = False
        # Set payment method domain
        res = self._onchange_journal()
        if not res.get('domain', {}):
            res['domain'] = {}
        jrnl_filters = self._compute_journal_domain_and_types()
        journal_types = jrnl_filters['journal_types']
        journal_types.update(['bank', 'cash'])
        res['domain']['journal_id'] = jrnl_filters['domain'] + [('type', 'in', list(journal_types))]
        return res

    def _compute_journal_domain_and_types(self):
        journal_type = ['bank', 'cash']
        domain = []
        if self.invoice_ids:
            domain.append(('company_id', '=', self.invoice_ids[0].company_id.id))
        if self.currency_id.is_zero(self.amount) and self.has_invoices:
            # In case of payment with 0 amount, allow to select a journal of type 'general' like
            # 'Miscellaneous Operations' and set this journal by default.
            journal_type = ['general']
            self.payment_difference_handling = 'reconcile'
        else:
            if self.payment_type == 'inbound':
                domain.append(('at_least_one_inbound', '=', True))
            else:
                domain.append(('at_least_one_outbound', '=', True))
        return {'domain': domain, 'journal_types': set(journal_type)}

    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        jrnl_filters = self._compute_journal_domain_and_types()
        journal_types = jrnl_filters['journal_types']
        domain_on_types = [('type', 'in', list(journal_types))]
        if self.invoice_ids:
            domain_on_types.append(('company_id', '=', self.invoice_ids[0].company_id.id))
        if self.journal_id.type not in journal_types or (self.invoice_ids and self.journal_id.company_id != self.invoice_ids[0].company_id):
            self.journal_id = self.env['account.journal'].search(domain_on_types, limit=1)
        return {'domain': {'journal_id': jrnl_filters['domain'] + domain_on_types}}

    @api.onchange('currency_id')
    def _onchange_currency(self):
        self.amount = abs(self._compute_payment_amount(self.invoice_ids, self.currency_id, self.journal_id, self.payment_date))

        if self.journal_id:  # TODO: only return if currency differ?
            return

        # Set by default the first liquidity journal having this currency if exists.
        domain = [('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)]
        if self.invoice_ids:
            domain.append(('company_id', '=', self.invoice_ids[0].company_id.id))
        journal = self.env['account.journal'].search(domain, limit=1)
        if journal:
            return {'value': {'journal_id': journal.id}}

    @api.model
    def _compute_payment_amount(self, invoices, currency, journal, date):
        '''Compute the total amount for the payment wizard.

        :param invoices:    Invoices on which compute the total as an account.invoice recordset.
        :param currency:    The payment's currency as a res.currency record.
        :param journal:     The payment's journal as an account.journal record.
        :param date:        The payment's date as a datetime.date object.
        :return:            The total amount to pay the invoices.
        '''
        company = journal.company_id
        currency = currency or journal.currency_id or company.currency_id
        date = date or fields.Date.today()

        if not invoices:
            return 0.0

        self.env['account.move'].flush(['type', 'currency_id'])
        self.env['account.move.line'].flush(['amount_residual', 'amount_residual_currency', 'move_id', 'account_id'])
        self.env['account.account'].flush(['user_type_id'])
        self.env['account.account.type'].flush(['type'])
        self._cr.execute('''
            SELECT
                move.type AS type,
                move.currency_id AS currency_id,
                SUM(line.amount_residual) AS amount_residual,
                SUM(line.amount_residual_currency) AS residual_currency
            FROM account_move move
            LEFT JOIN account_move_line line ON line.move_id = move.id
            LEFT JOIN account_account account ON account.id = line.account_id
            LEFT JOIN account_account_type account_type ON account_type.id = account.user_type_id
            WHERE move.id IN %s
            AND account_type.type IN ('receivable', 'payable')
            GROUP BY move.id, move.type
        ''', [tuple(invoices.ids)])
        query_res = self._cr.dictfetchall()

        total = 0.0
        for res in query_res:
            move_currency = self.env['res.currency'].browse(res['currency_id'])
            if move_currency == currency and move_currency != company.currency_id:
                total += res['residual_currency']
            else:
                total += company.currency_id._convert(res['amount_residual'], currency, company, date)
        return total

    def name_get(self):
        return [(payment.id, payment.name or _('Draft Payment')) for payment in self]

    @api.model
    def _get_move_name_transfer_separator(self):
        return '§§'

    @api.depends('move_line_ids.reconciled')
    def _get_move_reconciled(self):
        for payment in self:
            rec = True
            for aml in payment.move_line_ids.filtered(lambda x: x.account_id.reconcile):
                if not aml.reconciled:
                    rec = False
                    break
            payment.move_reconciled = rec

    def open_payment_matching_screen(self):
        # Open reconciliation view for customers/suppliers
        move_line_id = False
        for move_line in self.move_line_ids:
            if move_line.account_id.reconcile:
                move_line_id = move_line.id
                break
        if not self.partner_id:
            raise UserError(_("Payments without a customer can't be matched"))
        action_context = {'company_ids': [self.company_id.id], 'partner_ids': [self.partner_id.commercial_partner_id.id]}
        if self.partner_type == 'customer':
            action_context.update({'mode': 'customers'})
        elif self.partner_type == 'supplier':
            action_context.update({'mode': 'suppliers'})
        if move_line_id:
            action_context.update({'move_line_id': move_line_id})
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        for payment in self:
            if payment.invoice_ids:
                payment.destination_account_id = payment.invoice_ids[0].mapped(
                    'line_ids.account_id').filtered(
                        lambda account: account.user_type_id.type in ('receivable', 'payable'))[0]
            elif payment.payment_type == 'transfer':
                if not payment.company_id.transfer_account_id.id:
                    raise UserError(_('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
                payment.destination_account_id = payment.company_id.transfer_account_id.id
            elif payment.partner_id:
                if payment.partner_type == 'customer':
                    payment.destination_account_id = payment.partner_id.property_account_receivable_id.id
                else:
                    payment.destination_account_id = payment.partner_id.property_account_payable_id.id
            elif payment.partner_type == 'customer':
                default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
                payment.destination_account_id = default_account.id
            elif payment.partner_type == 'supplier':
                default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
                payment.destination_account_id = default_account.id

    @api.depends('move_line_ids.matched_debit_ids', 'move_line_ids.matched_credit_ids')
    def _compute_reconciled_invoice_ids(self):
        for record in self:
            reconciled_moves = record.move_line_ids.mapped('matched_debit_ids.debit_move_id.move_id')\
                               + record.move_line_ids.mapped('matched_credit_ids.credit_move_id.move_id')
            record.reconciled_invoice_ids = reconciled_moves.filtered(lambda move: move.is_invoice())
            record.has_invoices = bool(record.reconciled_invoice_ids)
            record.reconciled_invoices_count = len(record.reconciled_invoice_ids)

    def action_register_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''

        return {
            'name': _('PDC Payment'),
            'res_model': 'pdc.account.payment',
            'view_mode': 'form',
            'view_id': self.env.ref('post_dated_cheque_mgt_app.view_pdc_account_payment_invoice_form').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def unreconcile(self):
        """ Set back the payments in 'posted' or 'sent' state, without deleting the journal entries.
            Called when cancelling a bank statement line linked to a pre-registered payment.
        """
        for payment in self:
            if payment.payment_reference:
                payment.write({'state': 'sent'})
            else:
                payment.write({'state': 'posted'})

    def cancel(self):
        self.write({'state': 'cancelled'})

    def unlink(self):
        if any(bool(rec.move_line_ids) for rec in self):
            raise UserError(_("You cannot delete a payment that is already posted."))
        if any(rec.move_name for rec in self):
            raise UserError(_('It is not allowed to delete a payment that already created a journal entry since it would create a gap in the numbering. You should create the journal entry again and cancel it thanks to a regular revert.'))
        return super(account_payment, self).unlink()

    def _prepare_payment_moves(self):
        ''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
        to the 'create' method.

        Example 1: outbound with write-off:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |   900.0   |
        RECEIVABLE          |           |   1000.0
        WRITE-OFF ACCOUNT   |   100.0   |

        Example 2: internal transfer from BANK to CASH:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |           |   1000.0
        TRANSFER            |   1000.0  |
        CASH                |   1000.0  |
        TRANSFER            |           |   1000.0

        :return: A list of Python dictionary to be passed to env['account.move'].create.
        '''
        all_move_vals = []
        for payment in self:

            pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
            if not pdc_account_id:
                raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

            pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
            if not pdc_account_creditors_id:
                raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

            company_currency = payment.company_id.currency_id
            move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

            # Compute amounts.
            write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
            if payment.payment_type in ('outbound', 'transfer'):
                counterpart_amount = payment.amount
            else:
                counterpart_amount = -payment.amount

            # Manage currency.
            if payment.currency_id == company_currency:
                # Single-currency.
                balance = counterpart_amount
                write_off_balance = write_off_amount
                counterpart_amount = write_off_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
                write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
                currency_id = payment.currency_id.id

            # Manage custom currency on journal for liquidity line.
            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                # Custom currency on journal.
                if payment.journal_id.currency_id == company_currency:
                    # Single-currency
                    liquidity_line_currency_id = False
                else:
                    liquidity_line_currency_id = payment.journal_id.currency_id.id
                liquidity_amount = company_currency._convert(
                    balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
            else:
                # Use the payment currency.
                liquidity_line_currency_id = currency_id
                liquidity_amount = counterpart_amount

            # Compute 'name' to be used in receivable/payable line.
            rec_pay_line_name = ''
            if payment.payment_type == 'transfer':
                rec_pay_line_name = payment.name
            else:
                if payment.partner_type == 'customer':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Customer Payment")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Customer Credit Note")
                elif payment.partner_type == 'supplier':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Vendor Credit Note")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Vendor Payment")
                if payment.invoice_ids:
                    rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))


            liquidity_line_account = payment.payment_type in ('outbound','transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id
            if payment.payment_type == 'outbound':
                liquidity_line_account = pdc_account_creditors_id
            else:
                liquidity_line_account = pdc_account_id

            # Compute 'name' to be used in liquidity line.
            liquidity_line_name = payment.name
            if payment.payment_type == 'transfer':
                liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
            elif payment.payment_type == 'outbound':
                pdc_pay_name = str(self.env['account.account'].browse(pdc_account_creditors_id).name)+" : "+str(self.name)
                liquidity_line_name = pdc_pay_name
            else:
                pdc_pay_name = str(self.env['account.account'].browse(pdc_account_id).name)+" : "+str(self.name)
                liquidity_line_name = pdc_pay_name

            # ==== 'inbound' / 'outbound' ====

            move_vals = {
                'date': payment.payment_date,
                'ref': payment.communication,
                'journal_id': payment.journal_id.id,
                'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                'partner_id': payment.partner_id.id,
                'line_ids': [
                    # Receivable / Payable / Transfer line.
                    (0, 0, {
                        'name': rec_pay_line_name,
                        'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': payment.destination_account_id.id,
                        'payment_pdc_id': payment.id,
                    }),
                    # Liquidity line.
                    (0, 0, {
                        'name': liquidity_line_name,
                        'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                        'currency_id': liquidity_line_currency_id,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': liquidity_line_account,
                        'payment_pdc_id': payment.id,
                    }),
                ],
            }
            if write_off_balance:
                # Write-off line.
                move_vals['line_ids'].append((0, 0, {
                    'name': payment.writeoff_label,
                    'amount_currency': -write_off_amount,
                    'currency_id': currency_id,
                    'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                    'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                    'date_maturity': payment.payment_date,
                    'partner_id': payment.partner_id.commercial_partner_id.id,
                    'account_id': payment.writeoff_account_id.id,
                    'payment_pdc_id': payment.id,
                }))

            if move_names:
                move_vals['name'] = move_names[0]

            all_move_vals.append(move_vals)

            # ==== 'transfer' ====
            if payment.payment_type == 'transfer':
                journal = payment.destination_journal_id

                # Manage custom currency on journal for liquidity line.
                if journal.currency_id and payment.currency_id != journal.currency_id:
                    # Custom currency on journal.
                    liquidity_line_currency_id = journal.currency_id.id
                    transfer_amount = company_currency._convert(balance, journal.currency_id, payment.company_id, payment.payment_date)
                else:
                    # Use the payment currency.
                    liquidity_line_currency_id = currency_id
                    transfer_amount = counterpart_amount

                transfer_move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.destination_journal_id.id,
                    'line_ids': [
                        # Transfer debit line.
                        (0, 0, {
                            'name': payment.name,
                            'amount_currency': -counterpart_amount if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.company_id.transfer_account_id.id,
                            'payment_pdc_id': payment.id,
                        }),
                        # Liquidity credit line.
                        (0, 0, {
                            'name': _('Transfer from %s') % payment.journal_id.name,
                            'amount_currency': transfer_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance > 0.0 and balance or 0.0,
                            'credit': balance < 0.0 and -balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_journal_id.default_credit_account_id.id,
                            'payment_pdc_id': payment.id,
                        }),
                    ],
                }

                if move_names and len(move_names) == 2:
                    transfer_move_vals['name'] = move_names[1]

                all_move_vals.append(transfer_move_vals)
        return all_move_vals

    def validate_pdc_payment(self):
        """ Posts a payment used to pay an invoice. This function only posts the
        payment by default but can be overridden to apply specific post or pre-processing.
        It is called by the "validate" button of the popup window
        triggered on invoice form by the "Register Payment" button.
        """
        
        if any(len(record.invoice_ids) != 1 for record in self):
            # For multiple invoices, there is account.register.payments wizard
            raise UserError(_("This method should only be called to process a single invoice's payment."))

        return self.post()

    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        AccountMove = self.env['account.move'].with_context(default_type='entry')
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'posted' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
            if not pdc_account_id:
                raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

            pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
            if not pdc_account_creditors_id:
                raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.payment_date)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            moves = AccountMove.create(rec._prepare_payment_moves())
            moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()

            # Update the state / move before performing any reconciliation.
            move_name = self._get_move_name_transfer_separator().join(moves.mapped('name'))

            if rec.payment_type == 'outbound':
                rec.write({
                    'state': 'collect_cash',
                    'account_move_id':moves.id,
                    'communication':self.communication,
                    'pdc_account_creditors_id': pdc_account_creditors_id,
                    'move_name': move_name
                })
            
            elif rec.payment_type == 'inbound':
                rec.write({
                    'state': 'collect_cash',
                    'account_move_id':moves.id,
                    'communication':self.communication,
                    'pdc_account_id':pdc_account_id,
                    'move_name': move_name
                })


            if rec.payment_type in ('inbound', 'outbound'):
                # ==== 'inbound' / 'outbound' ====
                if rec.invoice_ids:
                    (moves[0] + rec.invoice_ids).line_ids \
                        .filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id)\
                        .reconcile()
            elif rec.payment_type == 'transfer':
                # ==== 'transfer' ====
                moves.mapped('line_ids')\
                    .filtered(lambda line: line.account_id == rec.company_id.transfer_account_id)\
                    .reconcile()

            else:
                rec.write({
                    'state': 'collect_cash',
                    'account_move_id':moves.id,
                    'communication':self.communication,
                    'pdc_account_id':pdc_account_id,
                    'move_name': move_name
                })


        return True




    def action_draft(self):
        moves = self.mapped('move_line_ids.move_id')
        moves.filtered(lambda move: move.state == 'posted').button_draft()
        moves.with_context(force_delete=True).unlink()
        self.write({'state': 'draft'})


    # collect cash
    def collect_cash_button(self):

        AccountMove = self.env['account.move'].with_context(default_type='entry')

        for payment in self:

            pdc_account_id = payment.company_id.pdc_account_id and payment.company_id.pdc_account_id.id
            if not pdc_account_id:
                raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

            pdc_account_creditors_id = payment.company_id.pdc_account_creditors_id and payment.company_id.pdc_account_creditors_id.id
            if not pdc_account_creditors_id:
                raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

            company_currency = payment.company_id.currency_id
            move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

            # Compute amounts.
            write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
            
            # Liquidity Part
            if payment.payment_type in ('outbound', 'transfer'):
                counterpart_amount = payment.amount
                liquidity_line_account = payment.payment_type in ('outbound','transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id
            else:
                counterpart_amount = payment.amount
                liquidity_line_account = pdc_account_id

            # Counter Part
            counterpart_line_account = payment.destination_account_id.id
            if payment.payment_type == 'outbound':
                counterpart_line_account = pdc_account_creditors_id
            else:
                counterpart_line_account = payment.payment_type in ('outbound','transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id

            # Manage currency.
            if payment.currency_id == company_currency:
                # Single-currency.
                balance = counterpart_amount
                write_off_balance = write_off_amount
                counterpart_amount = write_off_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
                write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
                currency_id = payment.currency_id.id

            # Manage custom currency on journal for liquidity line.
            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                # Custom currency on journal.
                if payment.journal_id.currency_id == company_currency:
                    # Single-currency
                    liquidity_line_currency_id = False
                else:
                    liquidity_line_currency_id = payment.journal_id.currency_id.id
                liquidity_amount = company_currency._convert(
                    balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
            else:
                # Use the payment currency.
                liquidity_line_currency_id = currency_id
                liquidity_amount = counterpart_amount

            # Compute 'name' to be used in receivable/payable line.
            rec_pay_line_name = ''
            if payment.payment_type == 'transfer':
                rec_pay_line_name = payment.name
            else:
                if payment.partner_type == 'customer':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Customer Payment")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Customer Credit Note")
                elif payment.partner_type == 'supplier':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Vendor Credit Note")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Vendor Payment")
                if payment.invoice_ids:
                    rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))

            # Compute 'name' to be used in liquidity line.
            liquidity_line_name = payment.name
            if payment.payment_type == 'transfer':
                liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
            elif payment.payment_type == 'outbound':
                liquidity_line_name = str(self.env['account.account'].browse(pdc_account_creditors_id).name)+" : "+str(self.name)
            else:
                liquidity_line_name = str(self.env['account.account'].browse(pdc_account_id).name)+" : "+str(self.name)

            # ==== 'inbound' / 'outbound' ====

            move_vals = {
                'date': payment.payment_date,
                'ref': payment.communication,
                'journal_id': payment.journal_id.id,
                'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                'partner_id': payment.partner_id.id,
                'line_ids': [
                    # Receivable / Payable / Transfer line.
                    (0, 0, {
                        'name': rec_pay_line_name,
                        'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': counterpart_line_account,
                        'payment_pdc_id': payment.id,
                    }),
                    # Liquidity line.
                    (0, 0, {
                        'name': liquidity_line_name,
                        'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                        'currency_id': liquidity_line_currency_id,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': liquidity_line_account,
                        'payment_pdc_id': payment.id,
                    }),
                ],
            }
            if write_off_balance:
                # Write-off line.
                move_vals['line_ids'].append((0, 0, {
                    'name': payment.writeoff_label,
                    'amount_currency': -write_off_amount,
                    'currency_id': currency_id,
                    'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                    'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                    'date_maturity': payment.payment_date,
                    'partner_id': payment.partner_id.commercial_partner_id.id,
                    'account_id': payment.writeoff_account_id.id,
                    'payment_pdc_id': payment.id,
                }))
            seq = payment.journal_id.sequence_id.next_by_id()
            move_vals['name'] = seq

            moves = AccountMove.create(move_vals)
            moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
            if moves:
                payment.state = "collect_cash"
                if payment.payment_type == 'outbound':
                    payment.write({
                        'account_move_id':moves.id,
                        'communication':payment.communication,
                        'pdc_account_creditors_id': pdc_account_creditors_id,
                    })
                else:
                    payment.write({
                        'account_move_id':moves.id,
                        'communication':payment.communication,
                        'pdc_account_id':pdc_account_id,
                    })

            return True

    def cash_deposit_button(self):
        for record in self:
            line_ids = []
            journal = record.journal_id
            if not journal.check_sequence_id:
                raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
            if not journal.check_sequence_id.active:
                raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
            name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()
            seq = journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()
            move_dict = {
                'name': seq or name,
                'date': fields.Date.today(),
                'ref': self.communication or '',
                'company_id': self.company_id.id,
                'journal_id': journal.id,
            }
            amount = record.amount
            if record.payment_type == 'outbound':
                debit_account_id = record.destination_account_id.id
                credit_account_id = record.pdc_account_creditors_id.id
            else:
                debit_account_id = record.pdc_account_id.id
                credit_account_id = record.destination_account_id.id

            if debit_account_id:
                debit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.account_move_id,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'payment_pdc_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': debit_account_id,
                    'date': record.payment_date,
                })
                line_ids.append(debit_line)

            if credit_account_id:
                credit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.account_move_id,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'payment_pdc_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': credit_account_id,
                    'date': record.payment_date,
                })
                line_ids.append(credit_line)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            move.post()
            return record.write({'state': 'deposited'})


    def cash_bounced_button(self):
        for record in self:
            line_ids = []
            journal = record.journal_id
            if not journal.check_sequence_id:
                raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
            if not journal.check_sequence_id.active:
                raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
            name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).check_sequence_idseq.next_by_id()
            seq = journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()
            move_dict = {
                'name': seq or name,
                'date': fields.Date.today(),
                'ref': self.communication or '',
                'company_id': self.company_id.id,
                'journal_id': journal.id,
            }
            amount = record.amount
            if record.payment_type == 'outbound':
                credit_account_id = record.destination_account_id.id
                debit_account_id = record.pdc_account_creditors_id.id
            else:
                debit_account_id = record.destination_account_id.id
                credit_account_id = record.pdc_account_id.id

            if record.payment_type == 'transfer':
                move_line_name = record.name
            else:
                move_line_name = _("PDC Payment")
                if record.invoice_ids:
                    move_line_name += ': '
                    for inv in record.invoice_ids:
                        # if inv.move_id:
                        if inv.state == 'posted':
                            move_line_name += inv.name + ', '
                    move_line_name = move_line_name[:len(move_line_name)-2]

            if debit_account_id:
                debit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.account_move_id,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'payment_pdc_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': debit_account_id,
                    'date': record.payment_date,
                    'name': move_line_name
                })
                line_ids.append(debit_line)

            if credit_account_id:
                credit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.account_move_id,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'payment_pdc_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': credit_account_id,
                    'date': record.payment_date,
                    'name': move_line_name
                })
                line_ids.append(credit_line)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            move.post()
            return record.write({'state': 'bounced'})

    
    def _get_move_vals(self, journal=None):
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        seq = journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        return {
            'name': seq or name,
            'date': fields.Date.today(),
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }






    # collect cash done then generate journal entries
    # _create_payment_entry
    def cash_pdc_done_button(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''
        self.ensure_one()

        pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
        if not pdc_account_id:
            raise UserError(_("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

        pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
        if not pdc_account_creditors_id:
            raise UserError(_("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

        journal = self.journal_id
        if not journal.check_sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.check_sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()
        seq = journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()

        move_dict = {
            'name': seq or name,
            'date': fields.Date.today(),
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

        cash_move_id = self.env['account.move'].create(self._prepare_payment_moves())
        cash_move_id.write(move_dict)

        pdc_pay_name = str('PDC Payment')+" : "+str(self.communication)
        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        for line in self.account_move_id.line_ids:
            if line.account_id in (

                    self.journal_id.default_debit_account_id,
                    self.journal_id.default_credit_account_id,
            ):
                liquidity_lines += line
            elif line.account_id.internal_type in ('receivable', 'payable') or line.partner_id == line.company_id.partner_id:
                counterpart_lines += line
            else:
                writeoff_lines += line

        if self.payment_type == 'outbound':
            counterpart_lines.write({'account_id':pdc_account_creditors_id})
            liquidity_lines.write({'name':pdc_pay_name})

        
            if not self.name:
                # Use the right sequence to set the name
                if self.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if self.partner_type == 'customer':
                        if self.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if self.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if self.partner_type == 'supplier':
                        if self.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if self.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                self.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.payment_date)
                if not self.name and self.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

        liquidity_lines.write({'name':pdc_pay_name})        
        posted_entry = cash_move_id.post()
        if posted_entry:
            self.state = 'posted'
        return posted_entry


    def cash_returned_button(self):
        for rec in self:
            return rec.write({'state': 'returned'})


    def action_invoice_cancel(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                if move.state != 'draft':
                    move.button_cancel()
                move.unlink()
            rec.write({
                'state': 'cancelled',
                'move_name': '',
            })

    def action_set_to_pdc_post(self):
        for rec in self:
            rec.account_move_id.button_cancel()
            rec.account_move_id.unlink()
            rec.write({
                'state': 'posted',
            })


    def pdc_due_date_remainder(self):
        today_date = datetime.today().date()
        setting = self.env['res.config.settings'].search([], limit=1)
        first = setting.notify_opt_first
        second = setting.notify_opt_second
        thired = setting.notify_opt_thired
        vendor_notify_check = setting.vendor_notify_check
        customer_notify_check = setting.customer_notify_check
        user_notify_check = setting.user_notify_check
        pdc_due_date_records = self.search([('due_date','>=',today_date)])
        template_id = self.env.ref('post_dated_cheque_mgt_app.pdc_due_date_template')
        auther = self.env.user
        for record in pdc_due_date_records:
            first_option = record.due_date - relativedelta(days=int(first))
            second_option = record.due_date - relativedelta(days= int(second))
            thired_option = record.due_date - relativedelta(days=int(thired))
            if first_option == today_date:
                template_id.sudo().with_context(auther=auther).send_mail(record.id, force_send=True)
            if second_option ==  today_date:
                   template_id.sudo().with_context(auther=auther).send_mail(record.id, force_send=True)
            if thired_option ==  today_date:
                template_id.sudo().with_context(auther=auther).send_mail(record.id, force_send=True)
        return True
