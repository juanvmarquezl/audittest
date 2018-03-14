# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time


def audit_purchase_order_state(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Órdenes de compra en excepción',
        'group': 'purchase',
        'data': [],
        'detail': u'Verifica la existencia de órdenes de compra en excepción. Ver: Compras -> Compras -> Solicitudes de presupuesto',
        }
    purchase_ids = lnk.execute(
        'purchase.order', 'search',
        [('date_order', '>=', date_start), ('date_order', '<=', date_end),
         ('state', 'in', ('except_picking', 'except_invoice'))])
    purchase = lnk.execute(
        'purchase.order', 'read', purchase_ids,
        ('name', 'date_order', 'state', 'partner_id', 'validator'))
    for p in purchase:
        if not res['data']:
            res['data'].append((
                'Pedido', 'Fecha', 'Cliente', 'Validada por', 'Estado'))
        res['data'].append((
            p['name'], p['date_order'], p['partner_id'][1],
            p['validator'][1], p['state']))
    if len(res['data']) == 1:
        res['data'] = []
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
