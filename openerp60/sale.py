# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time


def audit_sale_order_state(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Pedidos de venta en excepción',
        'group': 'sale',
        'data': [],
        'detail': u'Verifica la existencia de pedidos de venta en excepción',
        }
    sales_ids = lnk.execute(
        'sale.order', 'search',
        [('date_order', '>=', date_start), ('date_order', '<=', date_end),
         ('state', 'in', ('shipping_except', 'invoice_except'))])
    sales = lnk.execute(
        'sale.order', 'read', sales_ids,
        ('name', 'date_order', 'state', 'partner_id', 'user_id'))
    for s in sales:
        if not res['data']:
            res['data'].append((
                'Pedido', 'Fecha', 'Cliente', 'Vendedor', 'Estado'))
        res['data'].append((
            s['name'], s['date_order'], s['partner_id'][1],
            s['user_id'][1], s['state']))
    if len(res['data']) == 1:
        res['data'] = []
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
