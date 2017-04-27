from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import logging
import time
import datetime
import ctypes
import warnings
import os
#import csv
import shutil
import psycopg2
import codecs
import sys


_logger = logging.getLogger(__name__)
class tam_discountrule(osv.osv):
	_name='tam.discountrule'
	
	_columns = {
	    'name':fields.char('Discount Name', size = 150, required = True),
	    'category_id':fields.many2one('product.category', 'Category', required = True),
	    'discount':fields.float('Discount'),
	    
	}
	
	_sql_constraints = [('rule_uniq','unique(category, discount)','Category + Discount must be unique!')]


class tam_group(osv.osv):
	_name='tam.group'
	
	_columns = {
	    'name':fields.char('Discount Rule Group', size = 50, required = True),
	    'description':fields.char('Description', size = 1024),
	    'discountrule_ids':fields.many2many('tam.discountrule'),
	    'default_discount':fields.float('Default Discount'),
	    'active':fields.boolean('Active'),
	}
	
	_defaults = {
	    'active':True,
	}
	
	def get_product_discount(self, cr, uid, ids, product_ids, context ={}):
		records = self.browse(cr, uid, ids)
		record = records[0]
		cat_ids =self.pool.get('product.product').browse(cr, uid, product_ids)
		cat = cat_ids[0] 
		rules = record.discountrule_ids
		if group.default_discount:
			discount = group.default_discount
		else:
			discount = 0
		find_discount = False
		while not (find_discount):
			for rule in rules:
				if cat == rule.category_id.id:
					discount = rule.discount
					find_discount = True
					break
			cat = self.pool.get('product.category').browse(cr, uid, select = cat).parent_id.id
			if not (cat):
				_logger.debug('No discount rule found for %s!', cat_id)
				break
		return discount
 

class tam_user(osv.osv):
    _name= 'tam.user'
      
    _columns = {
        'partner_id': fields.many2one('res.partner','Partner', required = True),
        'group_id':fields.many2one('tam.group', 'VOS Group'),
        'name': fields.char('VOS User',size = 100),
        'email': fields.char('eMail', size = 100, required = True),
        'password': fields.char('Password',size = 20, required = True),
        'active': fields.boolean('Active'),
        'country':fields.many2one('res.country','Country'),
    
    }
    
    _defaults = {
        'active' : True,
    }
    
    _rec_name='email'
    _sql_constraints = [('email_uniq','unique(email)','This email address is already registered!')]

class tam_wishline(osv.osv):
    _name='tam.wishline'
    
    _columns = {
        'product_des': fields.text('Product Description', required = True),
        'product_id': fields.many2one('product.product', 'Product'),
        'name': fields.char('Wish', size = 100, required = True),
        'qty': fields.integer('Quantity', required = True),
        'time':fields.datetime('Order Time'),
        'buyer':fields.many2one('tam.user', 'VOS Buyer', required = True),
        'state':fields.selection([('draft','Draft'),('confirmed','Buyer Confirmed'),('accepted','Accepted'),('in_tam_order','In_VOS_Order'),('denied','Denied')],'State'),
        'tam_id':fields.many2one('tam.orderline','VOS Order Line id'),
        'buyer_notice':fields.text('Buyer Notice'),
        'seller_notice':fields.text('Seller Notice'),
        
    }    
    
    _defaults ={
        'state':'draft',
    }
    
    def wish_confirm(self, cr, uid, ids, context = {}):
        self.write(cr, uid, ids, {'state':'confirmed'})
        return True

    def wish_accept(self, cr, uid, ids, ontext = {}):
        self.write(cr, uid, ids, {'state':'accepted'})
        return True
    
    def wish_deny(self, cr, uid, ids, context = {}):
        self.write(cr, uid, ids, {'state':'denied'})
        return True
        
    def wish_to_order(self, cr, uid ,ids, context = {}):
        records = self.browse(cr, uid, ids)
        record = records[0]
        _logger.debug('Wish: %s', record)
        _logger.debug('Wish id: %s', record.id)
        id = self.pool.get('tam.orderline').create(cr, uid, {
            'product_id': record.product_id.id,
            'qty':record.qty,
            'buyer':record.buyer.id,
            'origin':str(record.id),
            'wish_id':record.id,
            'buyer_notice':record.buyer_notice,
            'seller_notice':record.seller_notice,
            })
            
        if id:
            self.write(cr, uid, ids, {'tam_id':id})
            self.write(cr, uid, ids, {'state':'in_tam_order'})
            
        return True
    
class tam_orderline(osv.osv):
    _name='tam.orderline'
    
    def _get_so_name(self, cr, uid, ids, field_name, arg, context = {}):
        result = {}
        records = self.browse(cr, uid, ids)
        for record in records:
            result[record.id] = record.so_id.name
        return result
        
    def _get_subtotal(self, cr, uid, ids, field_name, arg, context = {}):
        result = {}
        records = self.browse(cr, uid, ids)
        for record in records:
            result[record.id] = record.product_id.list_price * record.qty * (100 - record.discount) / 100
        return result

    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required = True),
        'product_name':fields.related('product_id','name_template',readonly = True, type = 'char',string = 'Product Name', size = 128),
        'qty': fields.integer('Oder Quantity', required = True),
        #zhang add virtual_avaulable field
        'verqty':fields.related('product_id','virtual_available',readonly = True, type = 'float',string = 'Verfuegbar Menge'),
        'time':fields.datetime('Order Init Time'),
        'confirm_time':fields.datetime('Order confirmed Time'),
        'buyer':fields.many2one('tam.user', 'VOS Buyer', required = True),
        'list_price':fields.related('product_id','list_price', readonly = True, type = 'float', string = 'Price'),
        'tax':fields.selection([(33,'Tax-free Export'),(37,'19% USt')], 'Tax'),
        'subtotal':fields.function(_get_subtotal, type = 'float', string = 'Subtotal', method = True),
        'state':fields.selection([('draft','Draft(Cart)'),('cancelled','Buyer Cancelled'),('confirmed','Buyer Confirmed'),('accepted','Accepted'),('in_so','In_SO'),('denied','Denied')],'State'),
        'tam_unit_price':fields.float('VOS Unit Price'),
        'origin':fields.char('This order comes from:', size = 50),
        'discount':fields.float('Discount'),
        'so_id':fields.many2one('sale.order','Sales Order id'),
        'so_id_name':fields.function(_get_so_name, type = 'char', string = 'Sales Order', method = True),
        'sol_id':fields.many2one('sale.order.line','Sales Order Line id'),
        'wish_id':fields.many2one('tam.wishline','VOS Wish Line id'),
        'buyer_notice':fields.text('Buyer Notice'),
        'seller_notice':fields.text('Seller Notice'),
    }
    
    _defaults = {
        'state':'draft',
    }
    
    def _get_partner_id(self,cr,uid, ids, context = {}):
        records = self.browse(cr, uid, ids)
        record = records[0]
        return record.buyer.partner_id.id
        
    
    def get_categ_id(self, cr, uid, ids, context = {}):
        records = self.browse(cr, uid, ids)
        record = records[0]
        return record.product_id.categ_id.id
        
    def get_group_id(self, cr, uid, ids, contex= {}):
        records = self.browse(cr, uid, ids)
        record = records[0]
        return record.buyer.group_id.id
        
    
    
    def get_categ_discount(self, cr, uid, ids, context ={}):
        records = self.browse(cr, uid, ids)
        record = records[0]        
        _logger.info('VOS orderline: %s', record)
        
        group_id = self.get_group_id(cr, uid, ids)
        if not (group_id):
            _logger.debug('No group for user %s', record.buyer.id)
            return 0
        
        cat_id = self.get_categ_id(cr, uid, ids)
        if not (cat_id):
            _logger.debug('No cat_id for product %s', record.product_id.id)
            return 0
        
        #group = self.pool.get('tam.group').browse(cr, uid, ids = group_id)[0] 
        group = self.pool.get('tam.group').browse(cr, uid, group_id)
        
        if not (group):
            _logger.debug('Cannot find group!')
            return 0
        _logger.debug('group.default_discount : %s', group.default_discount)
        _logger.debug('group.discountrule_ids : %s', group.discountrule_ids)
        if group.default_discount:
            discount = group.default_discount
        else:
            discount = 0
        
        rules = group.discountrule_ids
        
        
        # if no discount for given id defined, then look its parent. nested loop.
        cat = cat_id
        find_discount = False
        while not (find_discount):
            _logger.debug('start searching discount with cat = %s', cat)
            _logger.debug('start searching discount with rules = %s', rules)
            for rule in rules:
                _logger.debug('cat : %s ,rule.category_id : %s ', cat,rule.category_id.id)
                if cat == rule.category_id.id:
                    _logger.debug('searching for discount for category : %s', cat)
                    discount = rule.discount
                    find_discount = True
                    _logger.debug('find discount for category %s : %s', cat, discount)
                    break
                
            cat = self.pool.get('product.category').browse(cr, uid, select = cat).parent_id.id
            if not (cat):
                _logger.debug('No discount rule found for %s!', cat_id)
                break
        return discount        
    
    def apply_group_discount(self, cr, uid, ids, context = {}):
        _logger.debug('Applying discount....')

        disc = self.get_categ_discount(cr, uid, ids)
        _logger.debug('Applied discount: %s', disc)
        self.write(cr, uid, ids, {'discount':disc})
        return True
    
    def order_confirm(self, cr, uid, ids, context = {}):
        self.write(cr, uid, ids, {'state':'confirmed'})
        now = datetime.datetime.now()
        _logger.debug('confirm_time %s', now)
        self.write(cr, uid, ids, {'confirm_time':now})
        return True

    def order_accept(self, cr, uid, ids, context = {}):  
        self.write(cr, uid, ids, {'state':'accepted'})
        return True

    def order_in_so(self, cr, uid, ids, context = {}):
        
        records = self.browse(cr, uid, ids)
        record = records[0]
        id = self.pool.get('sale.order.line').create(cr, uid, {
        	'order_id' : record.so_id.id,
            'name' : '[' + record.product_id.default_code + '] ' + record.product_id.name,
            'product_id': record.product_id.id,
            'price_unit': record.product_id.product_tmpl_id.list_price,
            'tax_id': [(6,0,[record.tax])],
            'product_uom': record.product_id.uom_id.id,
            'product_uom_qty': record.qty,
            'discount': record.discount,
            })
        #fields = self.read(cr, uid, ids, fields = ['so_id','product_name','product_id'])
        #id = self.pool.get('sale.order.line').create(cr, uid, {
        #    'order_id' : fields[0]['so_id'][0],
        #    'name' : fields[0]['product_name'],
        #    'product_id': fields[0]['product_id'][0],
        #    })
        if id :
            self.write(cr, uid, ids, {'sol_id':id})
            self.write(cr,uid,ids,{'state':'in_so'})

        return True
        
