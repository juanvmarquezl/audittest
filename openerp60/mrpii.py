# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time


def __audit_tcv_mrp_check_picking(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': context.get('name', ''),
        'group': 'mrp',
        'data': [],
        'detail': context.get('detail', ''),
        'model': context.get('model', ''),
        'start': time.time(),
        }
    item_ids = lnk.execute(
        res['model'], 'search', [('date_end', '>=', date_start),
                                 ('date_end', '<=', date_end),
                                 ])
    item = lnk.execute(
        res['model'], 'read', item_ids,
        ('parent_id', 'date_start', 'date_end', 'state', 'picking_id',
         'task_info'))
    for i in item:
        data = {}
        if not res['data']:
            res['data'].append((
                'Referencia', 'Subproceso', 'Inicio', 'Fin', 'Estado',
                u'Albarán', u'Información'))
        if i['state'] == 'done' and i['picking_id']:
            picking = lnk.execute(
                'stock.picking', 'read', i['picking_id'][0],
                ('name', 'state'))
            if picking['state'] not in ('done', 'cancel'):
                data['picking_id'] = '%s: %s' % (picking['name'],
                                                 picking['state'])
        if data:
            process = __get_parent_process_data(i['parent_id'][0])
            res['data'].append((
                process['ref'], i['parent_id'][1], i['date_start'],
                i['date_end'], i['state'], data['picking_id'], i['task_info']))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def __get_parent_process_data(parent_id):
    subprocess = lnk.execute(
        'tcv.mrp.subprocess', 'read', parent_id,
        ['process_id'])
    process = lnk.execute(
        'tcv.mrp.process', 'read', subprocess['process_id'][0],
        ['ref', 'name'])
    return process


def audit_tcv_mrp_gangsaw_picking(context):
    context.update({
        'name': u'Albaranes de salida por Aserrados, no procesados',
        'detail': u'Los albaranes listados a continuación no han sido '
        'aprobados.',
        'model': 'tcv.mrp.gangsaw',
        })
    return __audit_tcv_mrp_check_picking(context)


def audit_tcv_mrp_finished_slab_picking(context):
    context.update({
        'name': u'Albaranes de entrada en Inventariar láminas, no procesados',
        'detail': u'Los albaranes listados a continuación no han sido '
        'aprobados. Deben aprobarse desde Manufactura II -> Procesos '
        'productivos -> Procesos productivos.',
        'model': 'tcv.mrp.finished.slab',
        })
    return __audit_tcv_mrp_check_picking(context)


def audit_tcv_mrp_waste_slab_state(context):
    """
    Valida la existencia de Mermas que se encuentren en estado != "Listo".
    Para solventar las "Mermas no procesadas" se deben marcar como "Listo"
    desde Manufactura II -> Procesos productivos -> Procesos productivos.
    """
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Mermas no procesados',
        'group': 'mrp',
        'data': [],
        'model': 'tcv.mrp.waste.slab',
        'detail': 'Para solventar las "Mermas no procesadas" se deben '
                  'marcar como "Listo" desde Manufactura II -> Procesos '
                  'productivos -> Procesos productivos.',
        'start': time.time(),
        }
    item_ids = lnk.execute(
        res['model'], 'search', [('date_end', '>=', date_start),
                                 ('date_end', '<=', date_end),
                                 ])
    item = lnk.execute(
        res['model'], 'read', item_ids,
        ('parent_id', 'date_start', 'date_end', 'state',
         'task_info'))
    for i in item:
        if not res['data']:
            res['data'].append((
                'Referencia', 'Subproceso', 'Inicio', 'Fin', 'Estado',
                u'Información'))
        if i['state'] != 'done':
            process = __get_parent_process_data(i['parent_id'][0])
            res['data'].append((
                process['ref'], i['parent_id'][1], i['date_start'],
                i['date_end'], i['state'], i['task_info']))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def audit_tcv_mrp_supplies_picking(context):
    """
    Valida el estado del proceso: Utilización de insumos de producción
    """
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Registros de utilización de insumos de producción '
                'pendientes',
        'group': 'mrp',
        'data': [],
        'detail': u'Los albaranes listados a continuación no han sido '
        u'aprobados. Ver: Manufactura II -> Procesos productivos -> '
        u'Utilización de insumos de producción',
        'model': 'tcv.mrp.production.supplies',
        'start': time.time(),
        }
    item_ids = lnk.execute(
        res['model'], 'search', [('date', '>=', date_start),
                                 ('date', '<=', date_end),
                                 ])
    item = lnk.execute(
        res['model'], 'read', item_ids,
        ('ref', 'date', 'name', 'state', 'picking_id'))
    for i in item:
        data = {}
        if not res['data']:
            res['data'].append((
                'Referencia', 'Fecha', 'Concepto', 'Estado', u'Albarán'))
        if i['state'] != 'done':
            res['data'].append((
                i['ref'], i['date'], i['name'] or '', i['state'], 'N/D'))
        if i['state'] == 'done' and i['picking_id']:
            picking = lnk.execute(
                'stock.picking', 'read', i['picking_id'][0], ('name', 'state'))
            if picking['state'] not in ('done', 'cancel'):
                data['picking_id'] = '%s: %s' % (picking['name'],
                                                 picking['state'])
                res['data'].append((
                    i['ref'], i['date'], i['name'] or '', i['state'],
                    data['picking_id']))
    if len(res['data']) == 1:
        res['data'] = []
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
