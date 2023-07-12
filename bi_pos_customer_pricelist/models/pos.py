# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from datetime import date, time, datetime


class pos_order(models.Model):
	_inherit = 'pos.order'

	def apply_customer_pricelist(self):
		partner_record = self
		main_dict = {}
		partner_record_browse =self.env['res.partner'].browse(partner_record.id)
		partner_price_list_id = partner_record_browse.property_product_pricelist.id
		product_obj = self.env['product.product']
		product_ids = product_obj.search([])
		
		product_pricelist = self.env['product.pricelist']
		product_pricelist.browse(partner_price_list_id)
		for product_id in product_ids:
			
			price = product_pricelist.price_get(product_id.id, qty=1, partner=None)
			price.update({'product_id':product_id.id })
			main_dict.update({product_id.id : price})
		return main_dict
	
	def apply_customer_pricelist_default(self, partner_price_list_id):
		main_dict = {}
		product_obj = self.env['product.product']
		product_ids = product_obj.search([])
		product_pricelist = self.env['product.pricelist']
		product_pricelist.browse(partner_price_list_id)
		for product_id in product_ids:
			
			price = product_pricelist.price_get(product_id.id, qty=1, partner=None)
			price.update({'product_id':product_id.id })
			main_dict.update({product_id.id : price})
		
		return main_dict
		


		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
