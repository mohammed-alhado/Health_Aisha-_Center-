from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil import relativedelta

class Invoice(models.Model):
    _inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
    _name = 'cashier.invoice'
    _order = "name desc"

    name = fields.Char(string="Invoice Number #", readonly=True)
    patient = fields.Char("Patient")
    # patient = fields.Many2one('oeh.medical.patient' , string="Patient",track_visibility='always', required=True)
    #partner_id = fields.Many2one(related='patient.partner_id')
    invoice_date = fields.Datetime(string="Invoice Time",default=lambda *a: datetime.now())
    invoice_line = fields.One2many('invoice.line','invoice_id',string="Lines")
    payment_line = fields.One2many('cashier.payment','invoice_id',string="Payments")
    ref = fields.Char(string="References")
    total_amount = fields.Float(string="Total Amount",compute="_compute_amount",readonly=True ,track_visibility='always')
    amount_due = fields.Float(string="Amount Due" , readonly=True, track_visibility='always')
    paid_amount = fields.Float(string="Paid Amount" , readonly=True, track_visibility='always')
    invoice_state = fields.Selection([('draft','Draft'),('in_payment','In Payment'),('paid','Paid'),('refunded','Refunded')] , string="State",track_visibility='always',default='draft')
    

    note = fields.Text(string="Notes")

    def print_cashier_invoice(self):
        return self.env.ref('cashier.action_report_cashier_invoice').report_action(self)

    @api.onchange('invoice_line')
    def _compute_amount(self):
        for invoice in self:
            total = 0
            for line in invoice.invoice_line:
                total += line.subtotal
            invoice.total_amount = total

    @api.onchange('total_amount')
    def change_due_amount(self):
        for invoice in self:
            invoice.amount_due = invoice.total_amount - invoice.paid_amount
            if invoice.paid_amount != 0:
                if invoice.paid_amount == invoice.total_amount: 
                    invoice.invoice_state = "paid"
                elif invoice.paid_amount > 0 :
                    invoice.invoice_state = "in_payment"

            # if invoice.amount_due == 0:
                

    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('cashier.invoice') or _('New')
            result = super(Invoice, self).create(vals)
            return result

    def register_payment(self):
        sessoin_id = self.get_user_session()
        if sessoin_id:
            wizard_form = self.env.ref('cashier.view_payment_wizard', False)
            wizard_model = self.env['payment.wizard']
            vals = {
                    'invoice_id':self.id,
                    'partner_id':self.patient ,#.partner_id.id,
                    'amount_due':self.amount_due,
                    'amount':self.amount_due
                    }
            new = wizard_model.create(vals)
            return {
                'name':"Payment details",
                'type': 'ir.actions.act_window',
                'res_model': 'payment.wizard',
                'res_id': new.id,
                'view_id':  self.env.ref('cashier.view_payment_wizard',False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'

            }

        else :
            raise Warning(_("please start session first"))

    def register_payment_down(self):
        sessoin_id = self.get_user_session()
        if sessoin_id:
            for invoice in self:
                domain = [('code','=','MISC')]
                payment_account = self.env['account.journal'].search(domain, limit=1)
                invoice.paid_amount += invoice.amount_due#payment.amount
                invoice.change_due_amount()
                vals = {
                    'invoice_id':invoice.id,
                    'partner_id':invoice.patient, #.partner_id.id,
                    # 'amount': self.amount,
                    'note': "paid from down payment",
                    'payment_account':payment_account.id,
                }
                p = self.env['cashier.payment'].create(vals)
                for line in self.invoice_line:
                    vals = {
                        'payment_id':p.id,
                        'account_id':line.account_id.id,
                        'paid_amount': line.subtotal - line.paid_amount
                    }
                    l = self.env['payment.account'].create(vals)
                    line.paid_amount += line.subtotal - line.paid_amount

        else :
            raise Warning(_("please start session first"))

    def register_cheque(self):
        sessoin_id = self.get_user_session()
        if sessoin_id:
            wizard_form = self.env.ref('cashier.view_cheque_wizard', False)
            wizard_model = self.env['cheque.wizard']
            vals = {
                    'invoice_id':self.id,
                    'amount':self.amount_due,
                    'amount_due':self.amount_due
                    }
            new = wizard_model.create(vals)
            return {
                'name':"Cheque details",
                'type': 'ir.actions.act_window',
                'res_model': 'cheque.wizard',
                'res_id': new.id,
                'view_id':  self.env.ref('cashier.view_cheque_wizard',False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'

            }

        else :
            raise Warning(_("please start session first"))

    def refund(self):
        sessoin_id = self.get_user_session()
        if sessoin_id:
            wizard_form = self.env.ref('cashier.view_refund_wizard', False)
            wizard_model = self.env['refund.wizard']
            vals = {
                    'invoice_id':self.id,
                    'partner_id':self.patient ,#.partner_id.id,
                    'amount':self.paid_amount
                    }
            new = wizard_model.create(vals)
            return {
                'name':"Payment details",
                'type': 'ir.actions.act_window',
                'res_model': 'refund.wizard',
                'res_id': new.id,
                'view_id':  self.env.ref('cashier.view_refund_wizard',False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'

            }
            # for invoice in self:
            #     invoice.paid_amount += -invoice.paid_amount
            #     invoice.change_due_amount()
            #     account = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
            #     vals = {
            #         'invoice_id':invoice.id,
            #         'partner_id':invoice.patient.partner_id.id,
            #         'amount': -invoice.total_amount,
            #         'note':invoice.note,
            #         'payment_account':account.id,
            #     }
            #     p = self.env['cashier.payment'].create(vals)
                
            #     for line in invoice.invoice_line:
            #         vals = {
            #                 'payment_id':p.id,
            #                 'account_id':line.account_id.id,
            #                 'paid_amount': -line.paid_amount
            #         }
            #         l = self.env['payment.account'].create(vals)

            #         line.paid_amount += -line.paid_amount

            #     invoice.invoice_state = "refunded"

        else :
            raise Warning(_("please start session first"))

    def get_user_session(self):
        session_obj = self.env['cashier.session']
        domain = [('cashier', '=', self.env.uid),('state','=','in_progress')]
        sessoin_ids = session_obj.search(domain, limit=1)
        return sessoin_ids.id

class InvoiceLines(models.Model):
    _name = 'invoice.line'
    _rec_name = "item_id"
    invoice_id = fields.Many2one('cashier.invoice',string="invoice #")
    item_id = fields.Many2one('product.template',string="Item",required=True)
    qty = fields.Float(string="Quantity" , default=lambda *a: 1.0)
    price = fields.Float(string="Price", readonly=True ,default=lambda self: self.item_id.list_price)
    subtotal = fields.Float(string="Subtotal", readonly=True)
    account_id = fields.Many2one('account.account',string="Account" , readonly=True)
    paid_amount= fields.Float("Paid Amount", readonly=True)
    note = fields.Char(string="Notes")


    @api.onchange('item_id')
    def onchange_item(self):
        self.price = self.item_id.list_price
        
        if self.item_id.property_account_income_id:
            self.account_id = self.item_id.property_account_income_id
        else :
            self.account_id = self.item_id.categ_id.property_account_income_categ_id.id


    @api.onchange('item_id','qty','price')
    def compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.price

    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        product = self.env['product.product']
        for line in self:
            price_unit = line.price
            item_in_product = product.search([('name','=',line.item_id.name)],limit=1)
            template = {
                'name': line.item_id.name or '',
                'product_id': item_in_product.id,
                'product_uom': line.item_id.uom_id.id,
                'location_id': picking.picking_type_id.default_location_src_id.id,
                'location_dest_id': line.invoice_id.patient.partner_id.property_stock_customer.id,
                'picking_id': picking.id,
                'state': 'draft',
                'company_id': self.env.company.id,
                'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            
            diff_quantity = line.qty
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done