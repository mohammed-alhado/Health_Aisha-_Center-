# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	pdc_account_id = fields.Many2one('account.account',string="PDC Receivable Account", related='company_id.pdc_account_id', readonly=False)
	pdc_account_creditors_id = fields.Many2one('account.account',string="PDC Payable Account", related='company_id.pdc_account_creditors_id', readonly=False)

	customer_notify_check = fields.Boolean(string="Due Date Notification for Customer", related='company_id.customer_notify_check', readonly=False)
	vendor_notify_check = fields.Boolean(string="Due Date Notification for Vendor", related='company_id.vendor_notify_check', readonly=False)
	user_notify_check = fields.Boolean(string="Due Date Notification for User", related='company_id.user_notify_check', readonly=False)
	notify_opt_first = fields.Integer("Notify Befor Days",related='company_id.notify_opt_first', readonly=False)
	notify_opt_second = fields.Integer("Notify Befor Days",related='company_id.notify_opt_second', readonly=False)
	notify_opt_thired = fields.Integer("Notify Befor Days",related='company_id.notify_opt_thired', readonly=False)
