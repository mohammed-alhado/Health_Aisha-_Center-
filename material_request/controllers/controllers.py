# -*- coding: utf-8 -*-
# from odoo import http


# class Doctor(http.Controller):
#     @http.route('/doctor/doctor/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/doctor/doctor/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('doctor.listing', {
#             'root': '/doctor/doctor',
#             'objects': http.request.env['doctor.doctor'].search([]),
#         })

#     @http.route('/doctor/doctor/objects/<model("doctor.doctor"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('doctor.object', {
#             'object': obj
#         })
