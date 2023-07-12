# -*- coding: utf-8 -*-

import calendar
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, api
from odoo.http import request


class DashBoard(models.Model):
    _inherit = 'hms.reception'

    @api.model
    def get_clinic_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.clinic_amount
        return income
    @api.model
    def get_image_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.image_amount
        return income
    @api.model
    def get_surgery_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.surgery_amount
        return income
    @api.model
    def get_dental_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.dental_amount
        return income
    @api.model
    def get_lab_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.lab_amount
        return income
    @api.model
    def get_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.subtotal
        return income
    @api.model
    def get_today_expense(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.request.expense"].search([("request_time",">",start_date),("request_time","<",end_date)])
        expense = 0
        for r in request:
            expense += r.amount
        return expense
    @api.model
    def get_net_today_income(self, *post):
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request = self.env["hms.request.expense"].search([("request_time",">",start_date),("request_time","<",end_date)])
        expense = 0
        for r in request:
            expense += r.amount
        request = self.env["hms.reception"].search([("request_time",">",start_date),("request_time","<",end_date)])
        income = 0
        for r in request:
            income += r.subtotal
        
        return income - expense