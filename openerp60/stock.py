# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time
# ~ import datetime


def audit_tcv_stock_changes(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Ajustes a lotes de inventario pendientes',
        'group': 'stock',
        'data': [],
        'detail': u'Se deben aprobar los albaranes correspondientes. '
                  'Primero la salida y luego la entrada.',
        }
    changes_ids = lnk.execute(
        'tcv.stock.changes', 'search',
        [('date', '>=', date_start), ('date', '<=', date_end)])
    changes = lnk.execute(
        'tcv.stock.changes', 'read', changes_ids,
        ('ref', 'date', 'state', 'picking_out_id', 'picking_in_id'))
    for c in changes:
        data = {}
        if not res['data']:
            res['data'].append((
                'Ajuste', 'Fecha', 'Estado', 'Alb. salida', 'Alb. Entrada'))
        if c['state'] not in ('done', 'cancel'):
            data['state'] = c['state']
        if c['picking_out_id']:
            picking = lnk.execute(
                'stock.picking', 'read', c['picking_out_id'][0],
                ('name', 'state'))
            if picking['state'] not in ('done', 'cancel'):
                data['picking_out_id'] = '%s: %s' % (picking['name'],
                                                     picking['state'])
        if c['picking_in_id']:
            picking = lnk.execute(
                'stock.picking', 'read', c['picking_in_id'][0],
                ('name', 'state'))
            if picking['state'] not in ('done', 'cancel'):
                data['picking_in_id'] = '%s: %s' % (picking['name'],
                                                    picking['state'])
        if data:
            res['data'].append((
                c['ref'], c['date'], c['state'],
                data.get('picking_out_id', ''),
                data.get('picking_in_id', '')))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def audit_tcv_bundle_status(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Estatus de bundles de exportación',
        'group': 'stock',
        'data': [],
        'detail': u'Comprueba la disponibilidad real de los bundles de ' +
                  u'exportación y el peso. Deben ajustarse los campos ' +
                  u'según corresponda. Almacen -> Trazabilidad -> Bulto. ' +
                  u'(No se usa límite de fechas)',
        }
    bundles_ids = lnk.execute(
        'tcv.bundle', 'search',
        [('date', '>=', date_start), ('date', '<=', date_end)])
    bundles = lnk.execute(
        'tcv.bundle', 'read', bundles_ids,
        ('name', 'line_ids', 'weight_net', 'location_id', 'product_id',
         'reserved'))
    parent_ids = lnk.execute(
        'stock.location', 'search', [('name', '=', u'Exportación')])
    export_locations = lnk.execute(
        'stock.location', 'search', [('location_id', 'in', parent_ids)])
    for b in bundles:
        #~ data = {}
        obs = []
        if not b['weight_net'] and not b['reserved']:
            obs.append('Peso 0')
        if not b['location_id'] and not b['reserved']:
            obs.append(u'Bundle sin Ubicación')
        tracking_id = lnk.execute(
            'stock.tracking', 'search', [('name', '=', b['name'])])
        if b['reserved']:  # Reservados
            if not tracking_id:
                obs.append(u'Bundle reservado sin Paquete asociado')
        else:  # Disponibles
            if b['location_id'] and \
                    b['location_id'][0] not in export_locations:
                obs.append(u'Ubicación incorrecta para exportación')
            if tracking_id:
                obs.append(u'Bundle disponible con Paquete asociado')
            location_errors = []
            #~ Validar ubicacion de lotes = ubic. bundle (Solo disponibles)
            for l in b['line_ids']:
                if b['location_id']:
                    line = lnk.execute(
                        'tcv.bundle.lines', 'read', l, ['prod_lot_id'])
                    lot_location = lnk.execute(
                        'stock.production.lot', 'get_actual_lot_location',
                        line['prod_lot_id'][0])
                    if not lot_location or \
                            lot_location[0] != b['location_id'][0]:
                        location_errors.append(
                            line['prod_lot_id'][1].split(' ')[0])
            if location_errors:
                obs.append(u'Ubicación distinta bundle y lote: %s' %
                           ', '.join(location_errors))
        if not b['line_ids']:
            obs.append('Bundle sin lotes')
        if obs:
            if not res['data']:
                res['data'].append((
                    'Bundle', 'Producto', u'Ubicación', 'Peso',
                    u'Observaciones'))
            res['data'].append((
                b['name'],
                b['product_id'][1],
                b['location_id'] and b['location_id'][1] or '',
                b['weight_net'],
                u', '.join(obs) + '.'))
    return res


def check_steel_grit_bags_25(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Movimientos de granalla no múltiplos de 25Kg',
        'group': 'stock',
        'data': [],
        'detail': u'Verifica que las cantidades indicadas en los '
                  u'movimientos de stock de granalla sean múltiplos de 25Kg',
        }
    categ_ids = lnk.execute(
        'product.category', 'search', [('name', '=', u'GRANALLA')])
    product_ids = lnk.execute(
        'product.product', 'search', [('categ_id', 'in', categ_ids)])
    move_ids = lnk.execute(
        'stock.move', 'search',
        [('date', '>=', date_start), ('date', '<=', date_end),
         ('product_id', 'in', product_ids), ('state', '!=', 'cancel')])
    moves = lnk.execute(
        'stock.move', 'read', move_ids,
        ('picking_id', 'product_uom', 'product_qty', 'product_id', 'date',
         'name', 'prodlot_id', 'state'))
    res['data'].append((
        u'Albarán', 'Producto', u'Lote', 'Cantidad', 'Fecha', u'Motivo',
        'Estado'))
    for m in moves:
        if m['product_uom'][0] == 2:
            qty = m['product_qty']
        elif m['product_uom'][0] == 6:
            qty = m['product_qty'] * 1000
        else:
            qty = -1
        if qty % 25:
            res['data'].append((
                m['picking_id'] and m['picking_id'][1] or '',
                m['product_id'] and m['product_id'][1] or '',
                m['prodlot_id'] and m['prodlot_id'][1] or '',
                '%.2f %s' % (qty, m['product_uom'][1]),
                m['date'] and m['date'].split(' ')[0] or '',
                m['name'],
                m['state']
                ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_first_stock_move_no_internal(context):
    res = {
        'name': u'Primer movimiento de lotes',
        'group': 'stock',
        'data': [],
        'detail': u'Verifica que el primer movimiento registrado para un '
                  u'lote no tenga una ubicación "Interna" como origen. Si '
                  u'es el caso se deben ajustar la secuencia de los '
                  u'movimientos de inventario. Ocurre generalmente '
                  u'cuando se recibe un bloque antes de que sea facturado',
        }
    res['data'].append((
        u'Producto', u'Lote', u'Ubicación', u'Fecha'))
    sql = '''
        select p.name as product, o.name as lot, l.name as location, t.date
        from stock_move as t
        join (select a.prodlot_id , min(a.date) as date
              from stock_move as a group by a.prodlot_id)as t2
        on t.prodlot_id = t2.prodlot_id and t.date = t2.date
        left join stock_location l on t.location_id = l.id
        left join stock_production_lot o on t.prodlot_id = o.id
        left join product_template p on o.product_id = p.id
        where t.date >= '%(date_start)s' and  l.usage = 'internal' and
              t.state='done'
        order by 1, 2
        ''' % context
    for data in lnk.execute_sql(sql):
        # ~ print data
        res['data'].append((
            data[0].decode('utf-8'),
            data[1].decode('utf-8'),
            data[2].decode('utf-8'),
            data[3].strftime('%d/%m/%Y')
            ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_blocks_stock(context):

    res = {
        'name': u'Bloques con Stock menor a 1 m3 o bloques con costo 0',
        'group': 'stock',
        'data': [],
        'detail': u'Verifica que los bloques en Stock sean mayores a 1 m3 '
                  u'o que estos tengan costo 0',
        }
    res['data'].append((
        u'Producto',
        u'Lote',
        u'Cantidad',
        u'Costo',
        u'Observaciones',
        ))
    categ_id = lnk.execute(
        'product.category', 'search', [('name', '=', 'BLOQUES')])
    report_id = lnk.execute(
        'tcv.stock.by.location.report', 'create', {
            'date': time.strftime('%Y-%m-%d'),
            'categ_id': categ_id[0],
            'report_type': 'normal'
            })
    lnk.execute(
        'tcv.stock.by.location.report', 'button_load_inventory', [report_id])
    line_ids = lnk.execute(
        'tcv.stock.by.location.report.lines', 'search',
        [('line_id', '=', report_id)])
    lines = lnk.execute(
        'tcv.stock.by.location.report.lines', 'read', line_ids,
        ['product_id', 'prod_lot_id', 'product_qty', 'total_cost'])
    for line in lines:
        if line['product_qty'] < 1 or line['total_cost'] < 1:
            obs = u'Stock de bloque menor a 1 m3' if line['product_qty'] < 1 \
                else u'Bloque sin costo'
            product = lnk.execute(
                'product.product', 'read', line['product_id'], ['name'])
            lot = lnk.execute(
                'stock.production.lot', 'read', line['prod_lot_id'], ['name'])
            res['data'].append((
                product['name'],
                lot['name'],
                line['product_qty'],
                line['total_cost'],
                obs
                ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def stock_move_granalla(context):
    res = {
        'name': u'Origen del movimiento de la granalla',
        'group': 'stock',
        'data': [],
        'detail': u'Verifica que el destino sea produccion y el origen '
                  u'distinto de patio de bloque',
        }
    res['data'].append((
        u'Origen',
        u'Destino',
        u'Producto',
        u'Observaciones',
        ))
    granalla = ('2926', '743', '744', '745')
    destino = ('3', '59', '51', '75', '27', '63', '87', '15')
    origen = ('12')
    move_ids = lnk.execute(
        'stock.move', 'search', [])
    move_id = lnk.execute(
        'stock.move', 'read', move_ids, ['location_id',
                                         'location_dest_id',
                                         'product_id'])
    for moves in move_id:
        if moves['product_id'][0] == granalla and ['location_id'][0] \
                == origen and ['location_dest_id'][0][0] != destino:
            print 'check'
            origen_name = lnk.excute(
                'stock.move', 'search', [('location_dest_id', '=', origen)])
            destino_name = lnk.excute(
                'stock.move', 'search', [('product_id', '=', destino)])
            product_name = lnk.excute(
                'product.product', 'search', [('product_id', '=', granalla)])
            print origen_name
            print destino_name
            print product_name
            res['data'].append((
                origen_name,
                destino_name,
                product_name,
                u'Origen de granalla distinto al Patio de bloque'
                ))
    if len(res['data']) == 1:
        res['data'] = []
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
