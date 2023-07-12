odoo.define('AccountingDashboard.AccountingDashboard', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    var currency;
    var ActionMenu = AbstractAction.extend({
        template: 'Invoicedashboard',
        events: {
            'click #clinic_income_today': 'clinic_income',
            'click #image_income_today': 'image_income',
            'click #surgery_income_today': 'surgery_income',
            'click #dental_income_today': 'dental_income',
            'click #lab_income_today': 'lab_income',
            'click #total_income_today': 'total_income',
            'click #total_expnese_today': 'total_expense',
            'click #net_income_today': 'net_income',
        },


        renderElement: function (ev) {
            var self = this;
            $.when(this._super())
                .then(function (ev) {

                    rpc.query({
                        model: "hms.reception",
                        method: "get_clinic_today_income",
                        
                    })
                        .then(function (result) {
                            var clinic_income = result;
                            if (clinic_income) {
                                $('#clinic_income_today').append('<span>' + clinic_income + '</span> <div class="title"></div>')
                            } else {
                                $('#clinic_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_image_today_income",
                        
                    })
                        .then(function (result) {
                            var image_income = result;
                            if (image_income) {
                                $('#image_income_today').append('<span>' + image_income + '</span> <div class="title"></div>')
                            } else {
                                $('#image_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_surgery_today_income",
                        
                    })
                        .then(function (result) {
                            var surgery_income = result;
                            if (surgery_income) {
                                $('#surgery_income_today').append('<span>' + surgery_income + '</span> <div class="title"></div>')
                            } else {
                                $('#surgery_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_dental_today_income",
                        
                    })
                        .then(function (result) {
                            var dental_income = result;
                            if (dental_income) {
                                $('#dental_income_today').append('<span>' + dental_income + '</span> <div class="title"></div>')
                            } else {
                                $('#dental_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_lab_today_income",
                        
                    })
                        .then(function (result) {
                            var lab_income = result;
                            if (lab_income) {
                                $('#lab_income_today').append('<span>' + lab_income + '</span> <div class="title"></div>')
                            } else {
                                $('#lab_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_today_expense",
                        
                    })
                        .then(function (result) {
                            var total_expense = result;
                            if (total_expense) {
                                $('#total_expnese_today').append('<span>' + total_expense + '</span> <div class="title"></div>')
                            } else {
                                $('#total_expnese_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_today_income",
                        
                    })
                        .then(function (result) {
                            var today_income = result;
                            if (today_income) {
                                $('#total_income_today').append('<span>' + today_income + '</span> <div class="title"></div>')
                            } else {
                                $('#total_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                    rpc.query({
                        model: "hms.reception",
                        method: "get_net_today_income",
                        
                    })
                        .then(function (result) {
                            var net_income = result;
                            if (net_income) {
                                $('#net_income_today').append('<span>' + net_income + '</span> <div class="title"></div>')
                            } else {
                                $('#net_income_today').append('<span>' + 0 + '</span> <div class="title"></div>')

                            }
                        })
                });
        },
       
        willStart: function () {
            var self = this;
            self.drpdn_show = false;
            return Promise.all([ajax.loadLibs(this), this._super()]);
        },
    });
    core.action_registry.add('invoice_dashboard', ActionMenu);

});