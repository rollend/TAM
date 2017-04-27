##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.netsvc
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
import openerp.addons.tam

_logger = logging.getLogger(__name__)
class tam_procedure(osv.osv_memory):
    _name = "tam.procedure"
    _description = "TAM Procedure"
    _columns = {
        'order_reference': fields.many2one('sale.order','Sales Order id'),
    }
    _defaults = {
        #'order_reference': False
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        orderline = self.pool.get('tam.orderline').browse(cr, uid, record_id, context=context)
		#checking order status?
        return False

    def orders_in_so(self, cr, uid, ids, context=None):
        records = self.browse(cr, uid, ids)
        record = records[0]
        order_obj = self.pool.get('tam.orderline')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        for o in order_obj.browse(cr, uid, context.get(('active_ids'), []), context=context):
			_logger.debug('Applying discount....')
			disc = o.get_categ_discount()
			_logger.debug('Applied discount: %s', disc)
			o.write({'discount':disc})		
			o.write({'state':'confirmed'})
			now = datetime.datetime.now()
			_logger.debug('confirm_time %s', now)
			o.write({'confirm_time':now})
			o.write({'state':'accepted'})

        	#for i in o.so_id:
			id = self.pool.get('sale.order.line').create(cr, uid, {
				'order_id' : record.order_reference.id,
				'name' : '[' + o.product_id.default_code + '] ' + o.product_id.name,
				'product_id': o.product_id.id,
				'price_unit': o.product_id.product_tmpl_id.list_price,
				'tax_id': [(6,0,[o.tax])],
				'product_uom': o.product_id.uom_id.id,
				'product_uom_qty': o.qty,
				'discount': o.discount,
			})
		#fields = self.read(cr, uid, ids, fields = ['so_id','product_name','product_id'])
		#id = self.pool.get('sale.order.line').create(cr, uid, {
		#    'order_id' : fields[0]['so_id'][0],
		#    'name' : fields[0]['product_name'],
		#    'product_id': fields[0]['product_id'][0],
		#    })
			if id :
				o.write({'sol_id':id})
				o.write({'so_id_name':record.order_reference.name})
				o.write({'state':'in_so'})

        return True

tam_procedure()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
