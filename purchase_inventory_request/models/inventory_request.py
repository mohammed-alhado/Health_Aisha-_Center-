from odoo import models, fields, api , _
import datetime
class InventoryRequest(models.Model):
    _name = 'inventory.request'

    name = fields.Char(string="Request #" , readonly=True)