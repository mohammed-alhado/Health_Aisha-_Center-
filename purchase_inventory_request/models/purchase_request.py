from odoo import models, fields, api , _
import datetime
class PurchaseRequest(models.Model):
    _name = 'purchase.request'

    name = fields.Char(string='Purchase Request #' , readonly=True)
    
    department = fields.Selection([('lab','Lab'),('image','Imaging')],string="Department")
    requestor = fields.Many2one('res.user',string="Requestor")
    request_line = fields.One2many('purchase.request.line','purchase_request', string="Request Lines")
    note = fields.Text(string="Note")
    state = fields.Selection([('draft','Draft'),('confirm','Confirmed'),('manager_confirm','Manager Confirmed'),('done','Done'),('canceled','Canceled')],string="state", default="draft")
    
    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or _('New')
            result = super(PurchaseRequest, self).create(vals)
            return result

    def set_confirm(self):
        self.write({'state': 'confirm'})

    def set_cancel(self):
        self.write({'state': 'canceled'})
    
    def set_manager_confirmed(self):
        self.write({'state': 'manager_confirm'})
    
    def set_done(self):
        self.write({'state': 'done'})
    
    def set_to_draft(self):
        self.write({'state': 'draft'})


class RequestLine(models.Model):
    _name = 'purchase.request.line'

    product = fields.Many2one('product.template' , string="product")
    qty = fields.Float('Qty')
    note = fields.Char('note')
    purchase_request = fields.Many2one('purchase.request',string="Request")
    