# -*- coding: utf-8 -*-


from odoo import fields, models

class Company(models.Model):
	_inherit = 'res.company'

	pdc_account_id = fields.Many2one('account.account',string="PDC Receivable Account")
	pdc_account_creditors_id = fields.Many2one('account.account',string="PDC Payable Account")

	customer_notify_check = fields.Boolean('Customer Due Date Notification')
	vendor_notify_check = fields.Boolean('Vendor Due Date Notification')
	user_notify_check = fields.Boolean("User Due Date Notification")
	notify_opt_first = fields.Integer("Notify Before Days")
	notify_opt_second = fields.Integer("Notify Before Days")
	notify_opt_thired = fields.Integer("Notify Before Days")

