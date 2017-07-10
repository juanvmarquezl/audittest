# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time
import calendar


def audit_get_periods(context):
    if context.get('account_periods'):
        return context.get('account_periods')
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    date = time.strptime(date_end, '%Y-%m-%d')
    y = date.tm_year
    m = date.tm_mon
    d = calendar.monthrange(y, m)[1]  # feb last day
    date_end = '%04d-%02d-%02d' % (y, m, d)
    period_ids = lnk.execute(
        'account.period', 'search',
        [('date_start', '>=', date_start), ('date_stop', '<=', date_end)])
    periods = lnk.execute(
        'account.period', 'read', period_ids, [])
    context.update({'account_periods': {
        'ids': period_ids,
        'periods': periods}})
    return period_ids


def audit_generic_99999_acounts_moves(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Movimientos en cuentas genéricas de CxC ó CxP',
        'group': 'account',
        'data': [],
        'detail': u'Los asientos aquí relacionados deben ser modificados '
                  u'para utilizar la cuenta específica de la empresa en '
                  u'lugar de la genérica.',
        'start': time.time(),
        }
    accounts = ('1110199999', '2180199999',  # CXC NACIONALES
                '1110399999', '2180299999',  # CXC RELACIONADAS
                '2120199999', '1110899999',  # CXP NACIONALES
                '2120399999', '1111099999',  # CXP RELACIONADAS
                '2120299999', '1110999999',  # CXP EXTERIOR
                )
    acc_ids = lnk.execute(
        'account.account', 'search', [('code', 'in', accounts)])
    line_ids = lnk.execute(
        'account.move.line', 'search', [('account_id', 'in', acc_ids),
                                        ('date', '>=', date_start),
                                        ('date', '<=', date_end),
                                        ])
    if line_ids:
        moves = lnk.execute(
            'account.move.line', 'read', line_ids,
            ('move_id', 'date', 'account_id', 'partner_id'))
        moves_ok = []
        for m in moves:
            name = m.get('move_id', ['', ''])[1]
            if name not in moves_ok:
                if not res['data']:
                    res['data'].append((
                        'Asiento', 'Fecha', 'Cuenta', 'Empresa'))
                res['data'].append((
                    name, m['date'], m['account_id'][1], m['partner_id'][1]))
                moves_ok.append(name)
    return res


def audit_opening_account_periods(context):
    #~ date_start = context.get('date_start')
    #~ date_end = context.get('date_end')
    res = {
        'name': u'Períodos contables abiertos',
        'group': 'account',
        'data': [],
        'detail': u'Verifica la cantidad de períodos contables '
                  u'abiertos al mismo tiempo (Máx 2).',
        'start': time.time(),
        }
    audit_get_periods(context)
    #~ period_ids = context.get('account_periods', {}).get('ids', [])
    periods = context.get('account_periods', {}).get('periods', [])
    opened = []
    for p in periods:
        if not p['special'] and p['state'] == 'draft':
            opened.append((
                p['name'],
                p['code'],
                p['date_start'],
                p['date_stop'],
                'Abierto',
                ))
    if len(opened) > 2:
        res['data'].append((
            u'Período', u'Código', 'Inicio', 'Fin', 'Estado'))
        res['data'].extend(opened)
    return res


def audit_closed_account_period_moves_state(context):
    #~ date_start = context.get('date_start')
    #~ date_end = context.get('date_end')
    res = {
        'name': u'Asientos abiertos en períodos cerrados',
        'group': 'account',
        'data': [],
        'detail': u'Verifica la existencia de asientos en borrador en '
                  u'períodos contables cerrados.',
        'start': time.time(),
        }
    audit_get_periods(context)
    #~ period_ids = context.get('account_periods', {}).get('ids', [])
    periods = context.get('account_periods', {}).get('periods', [])
    period_ids = []
    for p in periods:
        if not p['special'] and p['state'] == 'done':
            period_ids.append(p['id'])
    move_ids = lnk.execute(
        'account.move', 'search',
        [('period_id', 'in', period_ids), ('state', '!=', 'posted')])
    moves = lnk.execute(
        'account.move', 'read', move_ids,
        ('name', 'ref', 'journal_id', 'period_id', 'date', 'state'))
    if moves:
        res['data'].append((
            u'Número', 'Referencia', 'Diario', u'Período', 'Fecha', 'Estado'))
    for m in moves:
        res['data'].append((
            m.get('name') or '',
            m.get('ref') or 'N/A',
            m['journal_id'][1],
            m['period_id'][1],
            m['date'],
            u'No asentado',
            ))
    return res


def check_imex_purchase_orders(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Estado de órdenes de compra y facturas de importación',
        'group': 'account',
        'data': [],
        'detail': u'Verifica el estado de los documentos de compras '
                  u'de importación, con base en la lista de empresas '
                  u'registradas en los expedientes de importación.',
        'start': time.time(),
        }
    imex_ids = lnk.execute(
        'tcv.import.management', 'search', [('state', '!=', 'cancel')])
    imex = lnk.execute(
        'tcv.import.management', 'read', imex_ids, ['partner_id'])
    partner_ids = list(set([x['partner_id'][0] for x in imex]))
    order_ids = lnk.execute(
        'purchase.order', 'search',
        [('partner_id', 'in', partner_ids),
         ('date_order', '>=', date_start), ('date_order', '<=', date_end)])
    orders = lnk.execute(
        'purchase.order', 'read', order_ids,
        ['name', 'date_order', 'partner_id', 'invoice_ids', 'state',
         'pricelist_id', 'import_id', 'description'])
    data = [('Tipo', 'Ref/Nro', 'Fecha', 'Proveedor', u'Información')]
    for o in orders:
        obs_oc = []
        if o['state'] == 'except_invoice':
            obs_oc.append(u'Excepción de fatura')
        if o['state'] == 'draft':
            obs_oc.append(u'Solicitud de presupuesto')
        if o['pricelist_id'][0] == 8:
            obs_oc.append(u'Lista de precios incorrecta')
        if o['invoice_ids']:
            obs_inv = []
            invoices = lnk.execute(
                'account.invoice', 'read', o['invoice_ids'],
                ['journal_id', 'supplier_invoice_number', 'date_document',
                 'name', 'partner_id', 'expedient', 'dua_form_id', 'state',
                 'import_id'])
            for i in invoices:
                if i['journal_id'][0] != 6:
                    obs_inv.append(u'Diario: %s' % i['journal_id'][1])
                elif not i['dua_form_id']:
                    obs_inv.append(u'Falta DUA')
                if not i['import_id']:
                    obs_inv.append(u'Falta expediente importación')
                if i['state'] == 'draft':
                    obs_inv.append(u'En borrador')
                if obs_inv and i['name']:
                    obs_inv.append(i['name'])
            if obs_inv:
                data.append((
                    'INV',
                    i.get('supplier_invoice_number') or '',
                    i.get('date_document') or '',
                    i['partner_id'][1],
                    u', '.join(obs_inv) + '.'))
        if obs_oc:
            obs_oc.append(o.get('description') or '')
            data.append((
                'O/C',
                o['name'],
                o.get('date_order') or '',
                o['partner_id'][1],
                u', '.join(obs_oc) + '.'))
    if len(data) > 1:
        res['data'] = data
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
