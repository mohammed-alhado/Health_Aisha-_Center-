from odoo import fields, api, models, _
from odoo.exceptions import UserError
import datetime
from dateutil import relativedelta


class PaymentWizard(models.TransientModel):
    _name = 'payment.wizard'

    def get_default_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        return journal.id
        
    invoice_id = fields.Many2one("cashier.invoice", string="Invoice", readonly=True)
    partner_id = fields.Char("Partner")
    # partner_id = fields.Many2one('res.partner',string="Partner" , readonly=True)
    amount = fields.Float(string="Amount")
    amount_due = fields.Float(string="Amount Due",readonly=True)
    note = fields.Char(sting="Notes")
    payment_account = fields.Many2one('account.journal', domain="[('type', 'in', ('bank', 'cash'))]" , string="Payment Method", required=True, default=get_default_journal)

    line_account = fields.Many2one('invoice.line', domain="[('invoice_id' , '=' , invoice_id)]") #,('paid_amount','<','200')
    
    payment_by_cheque = fields.Boolean(string="Cheque")
    cheque_number = fields.Char("Cheque number")
    effected_date = fields.Date("Effected Date")
    cheque_bank = fields.Char("Bank of Cheque")
    def validate_payment(self):
        for payment in self:
            if payment.amount < payment.amount_due:
                if payment.line_account == False:
                    raise Warning(_("please select account"))
                else:
                    payment.invoice_id.paid_amount += payment.amount
                    payment.invoice_id.change_due_amount()
                    vals = {
                            'invoice_id':self.invoice_id.id,
                            'partner_id':self.partner_id , #.id,
                            'amount': self.amount,
                            'note':self.note,
                            'payment_account':self.payment_account.id,
                        }
                    p = self.env['cashier.payment'].create(vals)
                    
                    for line in payment.line_account:
                        vals = {
                                'payment_id':p.id,
                                'account_id':line.account_id.id,
                                'paid_amount': payment.amount
                            }
                        l = self.env['payment.account'].create(vals)
                        line.paid_amount += payment.amount
            elif payment.amount == payment.amount_due:
                payment.invoice_id.paid_amount += payment.amount
                payment.invoice_id.change_due_amount()
                vals = {
                        'invoice_id':self.invoice_id.id,
                        'partner_id':self.partner_id , #.id,
                        'amount': self.amount,
                        'note':self.note,
                        'payment_account':self.payment_account.id,
                    }
                p = self.env['cashier.payment'].create(vals)
                for line in payment.invoice_id.invoice_line:
                    vals = {
                            'payment_id':p.id,
                            'account_id':line.account_id.id,
                            'paid_amount': line.subtotal - line.paid_amount
                        }
                    l = self.env['payment.account'].create(vals)
                    line.paid_amount += line.subtotal - line.paid_amount
                    
            # if payment.invoice_id.insurance == 'true' :
            #     if payment.invoice_id.invoice_state == 'paid':
            #         for line in payment.invoice_id.invoice_line:
            #             account_id = line.account_id
            #         insurance_data = {
            #             'payment_date': datetime.datetime.now().date(),
            #             'patient': payment.invoice_id.patient.id,
            #             'insurance_company':payment.invoice_id.patient_insurance.id,
            #             'insurance_type':payment.invoice_id.patient_type.id,
            #             'company':payment.invoice_id.ins_company.id,
            #             'specialist':payment.invoice_id.specialist,
            #             'admission':payment.invoice_id.admission,
            #             'lab':payment.invoice_id.lab,
            #             'image':payment.invoice_id.image,
            #             'surgery':payment.invoice_id.surgery,
            #             'medical_service':payment.invoice_id.medical_service,
            #             'pharmacy':payment.invoice_id.pharmacy,
            #             'ultrasound':payment.invoice_id.ultrasound,
            #             'account_id':account_id.id
            #         }
                    
            #         in_ids = self.env['claim.company.insurance'].create(insurance_data)
            product = False
            for line in payment.invoice_id.invoice_line:
                if line.item_id.type == "product":
                    product = True
                    invoice_obj = self.env["account.move"]
                    inv_ids = []
                    curr_invoice = {
                        'partner_id': payment.partner_id, #.id,
                        'journal_id': self.env['account.journal'].search([('code','=','INV')])[0].id,
                        'state': 'draft',
                        'type':'entry',
                        'date':  datetime.date.today(),
                        'ref': "Customer invoice #" + str(payment.invoice_id.name),
                       
                    }
                    inv_ids = invoice_obj.create(curr_invoice)
                    inv_id = inv_ids.id

                    if inv_ids:
                        expense_account = line.item_id.categ_id.property_account_expense_categ_id.id
                        intrem_account = line.item_id.categ_id.property_stock_account_output_categ_id.id
                        list_value = []
                        
                        list_value.append((0,0, {
                            'account_id': intrem_account,
                            'partner_id': payment.partner_id,#.id,
                            'name':line.item_id.name,
                            'credit': line.qty * line.item_id.standard_price
                        }))
                        
                        # line_id._onchange_amount_currency()
                        list_value.append((0,0, {
                            'account_id': expense_account,
                            'partner_id': payment.partner_id,#.id,
                            'name':line.item_id.name,
                            'debit': line.qty * line.item_id.standard_price
                        }))
                        
                        inv_ids.write({'line_ids': list_value})
                        inv_ids.action_post()
            if product:
                picking_type = self.env["stock.picking.type"].search([("code","=","outgoing")],limit=1)
                location_id = picking_type.default_location_src_id
                # location
                pick = {
                        'picking_type_id': picking_type.id,
                        'partner_id': payment.partner_id.id,
                        'origin': payment.invoice_id.name, #self.name,
                        'location_dest_id': payment.partner_id.property_stock_customer.id,
                        'location_id': picking_type.default_location_src_id.id
                    }
                picking = self.env['stock.picking'].create(pick)
                moves = payment.invoice_id.invoice_line.filtered(
                    lambda r: r.item_id.type in ['product'])._create_stock_moves(picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()

                action = self.env.ref('stock.action_picking_tree_ready')
                result = action.read()[0]
                result.pop('id', None)
                result['context'] = {}
                result['domain'] = [('id', '=', picking.id)]
                pick_ids = sum([picking.id])
                if pick_ids:
                    res = self.env.ref('stock.view_picking_form', False)
                    result['views'] = [(res and res.id or False, 'form')]
                    result['res_id'] = pick_ids or False
                return result


           