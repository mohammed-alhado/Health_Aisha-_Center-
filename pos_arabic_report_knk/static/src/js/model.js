odoo.define('pos_arabic_report_knk.model', function (require) {
    "use strict";

    var models = require("point_of_sale.models");
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    models.load_fields("res.company", ["arabic_name", "company_footer",
                                                       "company_heading_1",
                                                       "company_heading_2",
                                                       "company_heading_3",
                                                       "company_heading_4",]);

    var _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function(){
            var orders = _super_Order.export_for_printing.call(this);
            orders.company.arabic_name = this.pos.company.arabic_name;
            orders.company.currency_id = this.pos.company.currency_id;

            if (document.getElementById('qrcode') == null) {
                document.body.innerHTML += "<div style=\"display: none;\" id=\"qrcode\"/>"
            }
            else{
                document.getElementById('qrcode').innerHTML = "";
            }


            if (document.getElementById('generate_barcode') == null) {
                document.body.innerHTML += "<div id=\"generate_barcode\" style=\"display: none;\"><svg id=\"barcode\" style=\"width: 94%;\"></svg></div>";
            }
            else{
                document.getElementById('generate_barcode').innerHTML = "<svg id=\"barcode\" style=\"width: 94%;\"></svg>";
            }
//            var qrcode = new QRCode("qrcode");

            function makeCode () {

                const seller_name_enc = _compute_qr_code_field(1, orders.company.name);
                const company_vat_enc = _compute_qr_code_field(2, orders.company.vat);
                const timestamp_enc = _compute_qr_code_field(3, orders.date.isostring);
                const invoice_total_enc = _compute_qr_code_field(4, orders.total_with_tax.toString());
                const total_vat_enc = _compute_qr_code_field(5, orders.total_tax.toString());
                const str_to_encode = seller_name_enc.concat(company_vat_enc, timestamp_enc, invoice_total_enc, total_vat_enc);
                var binary = '';
                for (let i = 0; i < str_to_encode.length; i++) {
                    binary += String.fromCharCode(str_to_encode[i]);
                }
                return btoa(binary);

            }
            function _compute_qr_code_field(tag, field) {
                const textEncoder = new TextEncoder();
                const name_byte_array = Array.from(textEncoder.encode(field));
                const name_tag_encoding = [tag];
                const name_length_encoding = [name_byte_array.length];
                return name_tag_encoding.concat(name_length_encoding, name_byte_array);
            }
            /*generate QRCode*/
            var qrcodjs = new QRCode("qrcode", {
                text: makeCode(),
                width: 100,
                height: 100,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.H
            });
            orders.qrcode_img = qrcodjs._oDrawing._elCanvas.toDataURL("image/png");

            JsBarcode("#barcode", orders.name.replace(_t('Order '),''));

            orders.reciept_barcode = document.getElementById('generate_barcode').innerHTML;

            document.getElementById('generate_barcode').innerHTML = "";


            return orders;
        },

    });
});
