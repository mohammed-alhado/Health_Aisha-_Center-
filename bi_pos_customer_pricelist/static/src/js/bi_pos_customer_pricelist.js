odoo.define('bi_pos_customer_pricelist.pos', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var popups = require('point_of_sale.popups');
	var rpc = require('web.rpc');
	var utils = require('web.utils');
	var _t = core._t;
	var pos_pricelist;
	var round_di = utils.round_decimals;
	var round_pr = utils.round_precision;

	var _super_posmodel = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({
		initialize: function (session, attributes) {
			var partner_model = _.find(this.models, function(model){ return model.model === 'res.partner'; });
			partner_model.fields.push('property_product_pricelist');
			return _super_posmodel.initialize.call(this, session, attributes);
		},
	});
	

   models.load_models({
		model: 'pos.order',
		fields: ['pricelist_id'],
		domain: function(self){ return [['session_id', '=', self.pos_session.name],['state', 'not in', ['draft', 'cancel']]]; },
		loaded: function(self, pos_order) {
			self.pos_order = pos_order;
		},
	});
	 
	models.load_models({
		model: 'product.pricelist',
		fields: ['id','name','currency_id','discount_policy','display_name','item_ids'],
		//domain: function(self) { return [ ['currency_id', '=', self.currency.id] ]; },
		domain: null,
		loaded: function(self, pricelists) {
			
			var pos_pricelist;
			var pos_pricelist_id = self.config.pricelist_id[0];
			self.db.get_pricelists_by_id = {};
			pricelists.forEach(function(pricelist) {
				self.db.get_pricelists_by_id[pricelist.id] = pricelist;
				if (pricelist.id == pos_pricelist_id) {
					self.pricelist = pricelist;
					pos_pricelist = pricelist;
				}
			});
			self.pricelists = pricelists;
		},
	});
	


	

	models.load_models({
		model: 'product.pricelist.item',
		fields: ['id', 'fixed_price', 'date_end', 'applied_on', 'min_quantity', 'percent_price', 'date_start', 'product_tmpl_id','product_id', 'pricelist_id', 'compute_price', 'categ_id', 'price_discount', 'price_round', 'price_surcharge', 'price_min_margin', 'price_max_margin','base','base_pricelist_id'],
		domain: null,
		loaded: function(self, pricelist_items) {
			self.pricelist_items = pricelist_items;
		},
	});
	
	models.load_models({
		model: 'res.currency',
		//fields: ['id','name','currency_id'],
		domain: null,
		loaded: function(self, currencies) {
			self.currencies = currencies;
		},
	});
	
	models.load_models({
			model:  'product.product',
			fields: ['display_name', 'list_price','price','pos_categ_id', 'taxes_id', 'barcode', 'default_code',
					 'to_weight', 'uom_id', 'description_sale', 'description', 'categ_id', 'product_tmpl_id','tracking'],
			//order:  ['sequence','name'],
			order:  _.map(['sequence','default_code','name'], function (name) { return {name: name}; }),
			domain: [['sale_ok','=',true],['available_in_pos','=',true]],
			context: function(self){ return {display_default_code: false }; },
			loaded: function(self, products){
				self.get_products = [];
				self.get_products_by_id = [];
				self.get_products = products;
				products.forEach(function(product) {
					self.get_products_by_id.push(product.id);
				});
				//self.db.add_products(products);
			},   
	});

	screens.PaymentScreenWidget.include({

		// ===============================
		init: function(parent,options){
			var self = this;
			this._super(parent,options);
		},
		
		validate_order:function(){
			var self=this;
			this._super();
			
			var order = this.pos.get_order();
			var list_of_product = $('.product');
			var entered_partner;
			var default_prclst_id = self.pos.config.pricelist_id[0];
			var default_fiscal_position_id = _.find(this.pos.fiscal_positions, function(fp) {
					return fp.id === self.pos.config.default_fiscal_position_id[0];
				});

			rpc.query({
				model: 'pos.order',
				method: 'apply_customer_pricelist_default',
				args: [default_prclst_id, default_prclst_id], //user_email
			
			}).then(function(output) {

				$.each(list_of_product, function(index, value) {
					
					var product = $(value).data('product-id');
					
					var entered_pricelist_id = default_prclst_id;
		
					for (var i = 0; i < output.length; i++) {
						var new_pricelist = output[i][product][entered_pricelist_id];
		
						var currency_sign = self.chrome.widget.order_selector.format_currency(new_pricelist);
						if (self.pos.db.product_by_id[product].to_weight)
							currency_sign += '/Kg';
				
						$(value).find('.price-tag').html(currency_sign);
		
						entered_partner = output;
					}
				});
			});
			
			order.fiscal_position = default_fiscal_position_id;
		},
		
			   

		// ===============================    
	});
	

  //models.Order.extend
	var _super = models.Order.prototype;
	models.Order = models.Order.extend({
		
		// the client related to the current order.
		set_client: function(client){
			var self = this;
			var selected_pricelist = self.pos.pricelist;
			_super.set_client.call(this, client);
			if (self.pos.chrome.screens != null) {
				if (client != null) {
					var partner_pricelist_id = client.property_product_pricelist[0];
					self.get_final_pricelist = self.pos.db.get_pricelists_by_id[partner_pricelist_id]
					self.apply_pricelist(partner_pricelist_id); 
					self.pos.pricelists.forEach(function(prclst) {
	     				if(prclst.id == partner_pricelist_id){
	     					self.pos.get_order().set_pricelist(prclst)
	     				}
	     			});
					self.pos.chrome.screens.clientlist.apply_pricelist();
				}
				_super.set_client.call(this, client);
			   }  
		},

		add_product: function (product, options) {
			var self = this;
			var order = self.pos.get_order();
			if(this.get_client()){
				var pricelist_order_id = this.get_client().property_product_pricelist[0];
			}
			_super.add_product.call(this, product, options);
			if (pricelist_order_id){
					self.apply_pricelist(pricelist_order_id); 
			}
		},
	
		
		
		apply_pricelist: function(pricelist_id){
			var self = this;
			var pricelist_items = self.pos.pricelist_items;
			var items = [];
			for (var i in pricelist_items){
				if(pricelist_items[i].pricelist_id[0] == pricelist_id){
					items.push(pricelist_items[i]);
				}
			}
			pricelist_items = [];
			var today = moment().format('YYYY-MM-DD');
			for (var i in items){
				if(((items[i].date_start == false) || (items[i].date_start <= today))
										&& ((items[i].date_end == false) || (items[i].date_end >= today)))
										{
											pricelist_items.push(items[i]);
										}
			}
			var global_items = [];
			var category_items = [];
			var category_ids = [];
			var product_product_items = [];
			var product_template_items = [];
			var product_product_ids = [];
			var product_template_ids = [];
			
			for(var i in pricelist_items){
				switch(pricelist_items[i].applied_on){
				case '3_global': global_items.push(pricelist_items[i]); break;
				case '2_product_category': category_items.push(pricelist_items[i]);
					category_ids.push(pricelist_items[i].categ_id[0]) ; break;
				case '1_product': product_template_items.push(pricelist_items[i]);
					product_template_ids.push(pricelist_items[i].product_tmpl_id[0]) ;break;
				case '0_product_variant': product_product_items.push(pricelist_items[i]);
					product_product_ids.push(pricelist_items[i].product_id[0]) ;break;
					
				}
			}
			
			

			var order = self.pos.get_order();
			var lines = order ? order.get_orderlines() : null;
			for (var l in lines){
				var product_product_item = self.find_pricelist_item(lines[l].product.product_tmpl_id, product_product_ids);
				var product_template_item = self.find_pricelist_item(lines[l].product, product_template_ids);
				var categ_item = self.find_pricelist_item(lines[l].product.categ_id[0], category_ids);
				var temp = -1;
				var new_price = lines[l].product.price;
				if(product_product_items){
					for(var j in product_product_items){
						
						if(product_product_items[j].product_id[0] == lines[l].product['id']){
						   if(lines[l].quantity >= product_product_items[j].min_quantity){
								if(temp < 0){
									temp = lines[l].quantity - product_product_items[j].min_quantity;
									new_price = self.set_price(lines[l], product_product_items[j]);
									lines[l].set_unit_price(new_price);
								}
								else if(temp > (lines[l].quantity - product_product_items[j].min_quantity) &&
									(lines[l].quantity - product_product_items[j].min_quantity) >= 0){
									
									temp = lines[l].quantity - product_product_items[j].min_quantity;
									new_price = self.set_price(lines[l], product_product_items[j]);
									lines[l].set_unit_price(new_price);
								}
							}else{
								lines[l].set_unit_price(lines[l].product.lst_price);
							}
						}
					}
					// lines[l].set_unit_price(new_price);
				}
			   
				if(product_template_items){
					for(var j in product_template_items){
						if(product_template_items[j].product_tmpl_id[0] == lines[l].product.product_tmpl_id){
						   if(lines[l].quantity >= product_template_items[j].min_quantity){
								if(temp < 0){
									temp = lines[l].quantity - product_template_items[j].min_quantity;
									new_price = self.set_price(lines[l], product_template_items[j]);
									lines[l].set_unit_price(new_price);
								}
								else if(temp > (lines[l].quantity - product_template_items[j].min_quantity) &&
									(lines[l].quantity - product_template_items[j].min_quantity) >= 0){
									
									temp = lines[l].quantity - product_template_items[j].min_quantity;
									new_price = self.set_price(lines[l], product_template_items[j]);
									lines[l].set_unit_price(new_price);
								}
							}else{
								lines[l].set_unit_price(lines[l].product.lst_price);
							}
						}
					}
				}

				if(categ_item){
					for(var j in category_items){
						if(category_items[j].categ_id[0] == lines[l].product.categ_id[0]){
						   if(lines[l].quantity >= category_items[j].min_quantity)
							{
								if(temp < 0){
									temp = lines[l].quantity - category_items[j].min_quantity;
									new_price = self.set_price(lines[l], category_items[j]);
									lines[l].set_unit_price(new_price);
									
								}
								else if(temp > (lines[l].quantity - category_items[j].min_quantity) &&
									(lines[l].quantity - category_items[j].min_quantity) >= 0){
									temp = lines[l].quantity - category_items[j].min_quantity;
									new_price = self.set_price(lines[l], category_items[j]);
									lines[l].set_unit_price(new_price);
									
								}
							}else{
								lines[l].set_unit_price(lines[l].product.lst_price);
							}
						}
					}
					
				}

//                if there are no rules set for product or category, we will check global pricelists
				if(global_items.length > 0){
					for(var j in global_items){
						if(lines[l].quantity >= global_items[j].min_quantity)
						{
							if(temp < 0){
								temp = lines[l].quantity - global_items[j].min_quantity;
								new_price = self.set_price(lines[l], global_items[j]);
								lines[l].set_unit_price(new_price);
							}
							else if(temp > (lines[l].quantity - global_items[j].min_quantity) &&
								(lines[l].quantity - global_items[j].min_quantity) >= 0){
								temp = lines[l].quantity - global_items[j].min_quantity;
								new_price = self.set_price(lines[l], global_items[j]);
								lines[l].set_unit_price(new_price);
							}
						}else{
								lines[l].set_unit_price(lines[l].product.lst_price);
							}
					}
				}


			}
		},
		
		set_price: function (line, item) {
			var self = this;
			var new_price = 0;
			if(item.compute_price == 'fixed'){
				new_price = item.fixed_price;
			}
			else if(item.compute_price == 'percentage'){
				
				new_price = line.product.lst_price -(line.product.lst_price * item.percent_price / 100);
				
			}
			else if(item.compute_price == 'formula'){
				
				new_price = line.product.lst_price

				if (item.base === 'pricelist') {
					var pricelist_items = self.pos.pricelist_items;
					for(var pr=0; pr < pricelist_items.length; pr++){
						if(pricelist_items[pr]['id'] == item.base_pricelist_id[0]){
							new_price = self.set_price(line, pricelist_items[pr])
						}
					}
					
				} else if (item.base === 'standard_price') {
					new_price = line.product.standard_price;
				}

				var price_limit = new_price;
				new_price = new_price - (new_price * (item.price_discount / 100));
				if (item.price_round) {
					new_price = round_pr(new_price, item.price_round);
				}
				if (item.price_surcharge) {
					new_price += item.price_surcharge;
				}
				if (item.price_min_margin) {
					new_price = Math.max(new_price, price_limit + item.price_min_margin);
				}
				if (item.price_max_margin) {
					new_price = Math.min(new_price, price_limit + item.price_max_margin);
				}
			}
			return new_price;
		},
		
		find_pricelist_item: function (id, item_ids) {
			for (var j in item_ids){
				if(item_ids[j] == id){
					return true;
					break;
				}
			}
			return false;
		},
		
		export_as_JSON: function() {
			var json = _super.export_as_JSON.apply(this,arguments);
			json.pricelist = this.pricelist;
			return json;
		},

	
	});

	gui.Gui.prototype.screen_classes.filter(function(el) { return el.name == 'clientlist'})[0].widget.include({
		
		init: function(parent, options){
			this._super(parent, options);
			
			
			this.apply_pricelist = function(){
			//apply_pricelist: function() {
				var self = this;
				//this._super();
				var selectedOrder = this.pos.get_order();
				
				
				var list_of_product = $('.product');
					
				var entered_partner;
				var partner_id = false
				if (selectedOrder.get_client() != null)
					partner_id = selectedOrder.get_client();

					
					rpc.query({
						model: 'pos.order',
						method: 'apply_customer_pricelist',
						args: [ partner_id ? partner_id.id : 0],
					
					}).then(function(output) {

						self.pos.currencies.forEach(function(currency) {
							var entered_currency_id = selectedOrder.get_final_pricelist.currency_id[0];
							
							if (currency.id == entered_currency_id) {
								self.pos.currency = currency;
								self.pos.currency.decimals = currency.decimal_places;
								return true;
							}
						});
						$.each(list_of_product, function(index, value) {
							
							var entered_pricelist_id = selectedOrder.get_final_pricelist.id;
							var product = $(value).data('product-id');
							
							for (var i = 0; i < output.length; i++) {
								var new_pricelist = output[i][product][entered_pricelist_id];
								
								var currency_sign = self.chrome.widget.order_selector.format_currency(new_pricelist);
								if (self.pos.db.product_by_id[product].to_weight)
									currency_sign += '/Kg';
									
								$(value).find('.price-tag').html(currency_sign);
							
								entered_partner = output;
							}
						});
						//selectedOrder.save_to_db();
						
						if (entered_partner){
								self.pos.get_products.forEach(function(product) {
								for (var i = 0; i < entered_partner.length; i++) {
									var entered_pricelist_id = selectedOrder.get_final_pricelist.id;
									product.price = entered_partner[i][product.id][entered_pricelist_id];
								}
							});
						}

						
						
						selectedOrder.save_to_db();   	
				});
				
			 }
			 
		},
		
		//=============================================================================================================
		save_changes: function(){
			var self = this;
			var order = this.pos.get_order();
			if( this.has_client_changed() ){
				var default_fiscal_position_id = _.find(this.pos.fiscal_positions, function(fp) {
					return fp.id === self.pos.config.default_fiscal_position_id[0];
				});
				if ( this.new_client && this.new_client.property_account_position_id ) {
					
					order.fiscal_position = _.find(this.pos.fiscal_positions, function (fp) {
						return fp.id === self.new_client.property_account_position_id[0];
					}) || default_fiscal_position_id;
				} 
				else if(!this.new_client){
					
					var list_of_product = $('.product');
					var entered_partner;
					var default_prclst_id = self.pos.config.pricelist_id[0];
					
					order.apply_pricelist(default_prclst_id);

					rpc.query({
						model: 'pos.order',
						method: 'apply_customer_pricelist_default',
						args: [default_prclst_id, default_prclst_id], //user_email
					
					}).then(function(output) {
		
						$.each(list_of_product, function(index, value) {
							
							var product = $(value).data('product-id');
							
							var entered_pricelist_id = default_prclst_id;
				
							for (var i = 0; i < output.length; i++) {
								var new_pricelist = output[i][product][entered_pricelist_id];
				
								var currency_sign = self.chrome.widget.order_selector.format_currency(new_pricelist);
								if (self.pos.db.product_by_id[product].to_weight)
									currency_sign += '/Kg';
						
								$(value).find('.price-tag').html(currency_sign);
				
								entered_partner = output;
							}
						});
					});
					
					order.fiscal_position = default_fiscal_position_id;
					
				}
				else {
					order.fiscal_position = default_fiscal_position_id;
				}

				order.set_client(this.new_client);
			}
		},
		//=============================================================================================================
		
		
		save_client_details: function(partner) {
			var self = this;
			
			var fields = {};
			this.$('.client-details-contents .detail').each(function(idx,el){
				fields[el.name] = el.value || false;
			});

			if (!fields.name) {
				this.gui.show_popup('error',_t('A Customer Name Is Required'));
				return;
			}
			
			if (this.uploaded_picture) {
				fields.image = this.uploaded_picture;
			}

			fields.id           = partner.id || false;
			fields.country_id   = fields.country_id || false;

			if (fields.property_product_pricelist) {
				fields.property_product_pricelist = parseInt(fields.property_product_pricelist, 10);
			} else {
				fields.property_product_pricelist = false;
			}

			rpc.query({
					model: 'res.partner',
					method: 'create_from_ui',
					args: [fields],
				})
				.then(function(partner_id){
					self.saved_client_details(partner_id);
				},function(type,err){
					self.gui.show_popup('error',{
						'title': _t('Error: Could not Save Changes'),
						'body': _t('Your Internet connection is probably down.'),
					});
				});
		},
		
		
	
	});
	
	
	var OrderlineSuper = models.Orderline;
	models.Orderline = models.Orderline.extend({
	
		set_quantity: function(quantity){
			var self = this;
			OrderlineSuper.prototype.set_quantity.call(this, quantity);
			
			if(self.order.get_client()){
				var pricelist_orderline_id = self.order.get_client().property_product_pricelist[0];
			}
			
			if (pricelist_orderline_id) { 
				this.order.apply_pricelist(pricelist_orderline_id); 
			}
		},
		
	});
	// End Orderline start
	
	

});
