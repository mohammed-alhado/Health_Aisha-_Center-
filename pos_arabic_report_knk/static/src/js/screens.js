odoo.define('pos_arabic_report_knk.screens', function (require) {
    "use strict";

    var screens = require("point_of_sale.screens");
    screens.ReceiptScreenWidget.include({
    	init: function(parent, options) {
            var self = this;
            this._super(parent, options);
        },
        handle_auto_print: function() {
	        if (this.should_auto_print()) {
	            setTimeout(function(){
		            this.print();
		        }, 1000);
	            if (this.should_close_immediately()){
	                this.click_next();
	            }
	        } else {
	            this.lock_screen(false);
	        }
	    },

    });
});