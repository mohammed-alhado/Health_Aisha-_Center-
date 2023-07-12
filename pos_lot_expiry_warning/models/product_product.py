# -*- coding: utf-8 -*-

from odoo import models, api, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def lot_expiry_check(self, args):
        lots = self.env['stock.production.lot'].search([('name', '=', args[0]), ('product_id', '=', self.id)])
        if len(lots) < 1:
            return 0
        else:
            if lots.alert_date and lots.alert_date < fields.Datetime.today():
                return lots.alert_date
            else:
                return 1
