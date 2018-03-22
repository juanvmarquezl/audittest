# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time
import calendar


# Cache for account_ids
__account_code_ids__ = {}


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


def get_account_id(code):
    if code in __account_code_ids__:
        return __account_code_ids__[code]
    ids = lnk.execute(
        'account.account', 'search', [('code', '=', code)])
    acc_id = ids and ids[0] or 0
    __account_code_ids__[code] = acc_id
    return acc_id


def actual_period(period):
    today = time.strftime('%Y-%m-%d')
    return today >= period['date_start'] and today <= period['date_stop']


def audit_get_trial_balance(context):
    audit_get_periods(context)
    if context.get('account_periods', {}).get('trial_balance_loaded'):
        return False
    for period in context.get('account_periods', {}).get('periods'):
        balance_id = lnk.execute(
            'tcv.trial.balance', 'create', {
                'date_from': period['date_start'],
                'date_to': period['date_stop'],
                'non_zero': False,
                'no_view': True,
                'total_view': False,
                'level': 0,
                'show_code': True,
                'use_ident': False,
                'acc_from_id': 0,
                'acc_to_id': 0,
                })
        lnk.execute(
            'tcv.trial.balance', 'load_wizard_lines', balance_id, {})
        balance = lnk.execute(
            'tcv.trial.balance', 'read', balance_id, [])
        line_ids = balance.pop('line_ids', [])
        balance['line_ids'] = lnk.execute(
            'tcv.trial.balance.lines', 'read', line_ids, [])
        period.update({'trial_balance': balance})
    context['account_periods']['trial_balance_loaded'] = True
    return False


def get_trial_balance_account(context, period_id, account_id):
    audit_get_trial_balance(context)
    for period in context.get('account_periods', {}).get('periods'):
        if period.get('id') == period_id:
            for line in period.get('trial_balance', {}).get('line_ids'):
                if line['account_id'] == account_id:
                    return line
    return {}


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


def check_sequence(params):
    doc_ids = lnk.execute(
        params['model'], 'search', params['filter'])
    f = params['field'][0]
    docs = lnk.execute(
        params['model'], 'read', doc_ids, [f])
    oos = []
    data = [x[f] for x in docs]
    invalids = ('False', False)
    for i in invalids:
        while i in data:
            data.remove(i)
    while '' in data:
        data.remove('')
    if params.get('trim_field'):
        data = [x[params['trim_field']:] for x in data]
    sec = [int(x.replace('-', '').replace('EX', '')) for x in data]

    sec.sort()

    for x in sec[:-1]:
        if x + 1 not in sec:
            oos.append(x)
    return oos and [str(x) for x in oos] or []


def append_document_sequence(res, params):
    docs = check_sequence(params)
    if docs:
        res['data'].append((
            params['name'],
            params['field'][1],
            ', '.join(docs),
            ))


def check_document_sequences(context):
    res = {
        'name': u'Verificar secuencia de documentos',
        'group': 'account',
        'data': [('Documento', 'Campo', 'Saltos de secuencia en')],
        'detail': u'Verifica que no existan saltos en la secuencia de '
                  u'los documentos.',
        }
    params = {
        'name': 'Facturas de venta (Nacionales)',
        'model': 'account.invoice',
        'filter': [('type', '=', 'out_invoice'),
                   ('date_invoice', '>=', context['date_start']),
                   ('date_invoice', '<=', context['date_end']),
                   ('state', '!=', 'draft'),
                   ('journal_id', '=', 8),
                   ],
        'field': ('number', u'Número'),
        }
    append_document_sequence(res, params)
    params = {
        'name': u'Facturas de venta (Exportacion)',
        'model': 'account.invoice',
        'filter': [('type', '=', 'out_invoice'),
                   ('date_invoice', '>=', context['date_start']),
                   ('date_invoice', '<=', context['date_end']),
                   ('state', '!=', 'draft'),
                   ('journal_id', '=', 280),
                   ],
        'field': ('number', u'Número'),
        }
    append_document_sequence(res, params)
    params = {
        'name': u'Notas de credito clientes (Nacionales)',
        'model': 'account.invoice',
        'filter': [('type', '=', 'out_refund'),
                   ('date_invoice', '>=', context['date_start']),
                   ('date_invoice', '<=', context['date_end']),
                   ('state', '!=', 'draft'),
                   ('journal_id', '=', 8),
                   ],
        'field': ('number', u'Número'),
        }
    append_document_sequence(res, params)
    params = {
        'name': 'Documentos de venta (Nro. control)',
        'model': 'account.invoice',
        'filter': [('type', 'in', ('out_invoice', 'out_refund')),
                   ('date_invoice', '>=', context['date_start']),
                   ('date_invoice', '<=', context['date_end']),
                   ('state', '!=', 'draft'),
                   ],
        'field': ('nro_ctrl', u'Número control'),
        }
    append_document_sequence(res, params)
    params = {
        'name': u'Comprobantes de retencion de IVA proveedores',
        'model': 'account.wh.iva',
        'filter': [('type', 'in', ('in_invoice', 'in_refund')),
                   ('date', '>=', context['date_start']),
                   ('date', '<=', context['date_end']),
                   ('state', 'in', ('done', 'cancel')),
                   ],
        'field': ('number', u'Número'),
        'trim_field': -8,
        }
    append_document_sequence(res, params)
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_customs_form_state(context):
    date_start = context.get('date_start')
    date_end = context.get('date_end')
    res = {
        'name': u'Estado de planilla de liquidacion de impuestos aduanales '
                u'F86',
        'group': 'account',
        'data': [],
        'detail': u'Verifica el estado de las planillas de impuestos '
                  u'aduanales (Forma 86) asociadas a expedientes de '
                  u'importación.',
        }
    imex_ids = lnk.execute(
        'customs.form', 'search', [('state', '=', 'draft'),
                                   ('date_liq', '>=', date_start),
                                   ('date_liq', '<=', date_end)])
    imex = lnk.execute(
        'customs.form', 'read', imex_ids,
        ['name', 'ref', 'dua_form_id', 'date_liq', 'state'])
    if imex:
        res['data'].append((
            u'Número', 'Referencia', 'DUA', 'Fecha', 'Estado'))
    for i in imex:
        res['data'].append((
            i.get('name') or '',
            i.get('ref') or 'N/A',
            i['dua_form_id'] and i['dua_form_id'][1] or '',
            i['date_liq'],
            u'Borrador',
            ))
    return res


def check_zero_balance_accounts(context):
    res = {
        'name': u'Cuentas que deben quedar con saldo 0 al cierre del período',
        'group': 'account',
        'data': [],
        'detail': u'Verifica que las cuentas seleccionadas tengan saldo 0 '
                  u'al cierre de los períodos contables correspondientes. Se '
                  u'omite el período actual.',
        }
    accounts = (
        '1132000001',  # IVA CRÉDITO FISCAL
        '1132000003',  # IVA CRÉDITO FISCAL EN IMPORTACIONES
        )
    audit_get_trial_balance(context)
    res['data'].append((
        u'Período', u'Cuenta', u'Saldo'))
    for period in context.get('account_periods', {}).get('periods'):
        if not actual_period(period):
            for acc in accounts:
                acc_id = get_account_id(acc)
                balance = get_trial_balance_account(
                    context, period['id'], acc_id)
                if balance.get('balance'):
                    res['data'].append((
                        period.get('code') or '',
                        balance.get('acc_name') or '',
                        balance.get('balance'),
                        ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_move_in_period_accounts(context):
    res = {
        'name': u'Cuentas que deben tener movimento cada período',
        'group': 'account',
        'data': [],
        'detail': u'Verifica que las cuentas seleccionadas tengan algún '
                  u'movimiento registrado en cada uno de los periodos. Se '
                  u'omite el período actual.',
        }
    accounts = (
        '1330199999',  # DEPR.ACUM.EDIFICIOS
        '1330299999',  # DEPR.ACUM.INSTALACIONES
        '1330399999',  # DEPR.ACUM.MAQUINARIAS
        '1330400003',  # AMORTIZACION CANTERA LA LIMONERA
        '1330400004',  # AMORTIZACION CANTERA EL CHIVITO
        '1330599999',  # DEPR.ACUM.VEHICULOS
        '1330699999',  # DEPR.ACUM.MOBILIARIOS Y EQUIPOS DE OFICINAS
        '1330799999',  # DEPR.ACUM.UTILES Y HERRAMIENTAS
        '1330899999',  # DEPR.ACUM.EQUIPOS DE COMPUTACION
        '1331099999',  # DEPR.ACUM.EQUIPOS DE SEGURIDAD INTERNA
        '2300100001',  # PROVISION ART.142 "A" GARANTIA PREST.SOC.(TRIM)
        '5135500100',  # DEPRECIACIÓN EDIFICIOS
        '5135500110',  # DEPRECIACIÓN INSTALACIONES Y MEJORAS
        '5135500120',  # DEPRECIACIÓN MAQUINARIA Y EQUIPO
        '5135500140',  # DEPRECIACIÓN VEHÍCULOS DE PLANTA
        '5135500150',  # DEPRECIACIÓN ÚTILES Y HERRAMIENTAS
        '7230900006',  # DEPRECIACIÓN  MOBILIARIO Y EQUIPO OFICINA
        '7230900008',  # DEPRECIACIÓN EQUIPOS DE COMPUTACIÓN
        #~ '7230900009',  # DEPRECIACIÓN EQUIPOS DE TELECOMUNICACIONES
        '7230900010',  # DEPRECIACIÓN EQUIPOS DE SEGURIDAD
        )
    audit_get_trial_balance(context)
    res['data'].append((
        u'Período', u'Cuenta', u'Movimientos'))
    for period in context.get('account_periods', {}).get('periods'):
        if not actual_period(period):
            for acc in accounts:
                acc_id = get_account_id(acc)
                balance = get_trial_balance_account(
                    context, period['id'], acc_id)
                if not balance.get('credit') and not balance.get('debit'):
                    res['data'].append((
                        period.get('code') or '',
                        balance.get('acc_name') or '',
                        float(balance.get('amount_period')),
                        ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_invalid_account_balance(context):
    res = {
        'name': u'Cuentas deudoras o acreedoras con saldo inverso',
        'group': 'account',
        'data': [],
        'detail': u'Verifica que las cuentas de activo no '
                  u'tengan saldo acreedor o del pasivo saldo deudor, a '
                  u'excepción de las cuentas de orden',
        }
    test = [
        {'search_options': [('code', '>', '1'),
                            ('code', '<', '2'),
                            ('type', '!=', 'view')],
         'type': 'Activo',
         'except': ["1121000180", "1121500180", "1121500280", "1121500380",
                    "1121500480", "1121500580", "1122000180", "1122000182",
                    "1123000180", "1125000180", "1129099999", "1330199999",
                    "1330299999", "1330399999", "1330400001", "1330400002",
                    "1330400003", "1330400004", "1330599999", "1330699999",
                    "1330799999", "1330899999", "1330999999", "1331099999",
                    ],
         },
        {'search_options': [('code', '>', '2'),
                            ('code', '<', '3'),
                            ('type', '!=', 'view')],
         'type': 'Pasivo',
         'except': [],
         }
        ]
    audit_get_trial_balance(context)
    res['data'].append((
        u'Período', u'Tipo', u'Cuenta', u'Saldo'))
    for t in test:
        accounts = lnk.execute(
            'account.account', 'search', t['search_options'])
        except_ids = lnk.execute(
            'account.account', 'search', [('code', 'in', t['except'])])
        for acc_id in accounts:
            for period in context.get('account_periods', {}).get('periods'):
                balance = get_trial_balance_account(
                    context, period['id'], acc_id)
                if acc_id not in except_ids and balance and (
                        (t['type'] == 'Activo' and
                         balance.get('balance') < 0) or
                        (t['type'] == 'Pasivo' and
                         balance.get('balance') > 0)):
                    res['data'].append((
                        period.get('code') or '',
                        t['type'],
                        balance.get('acc_name') or '',
                        float(balance.get('balance', 0.0)),
                        ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_reconcile_status(context):
    res = {
        'name': u'Estado de cuentas conciliables',
        'group': 'account',
        'data': [],
        'detail': u'Verifica que las cuentas "conciliables" no tengan mas de '
                  u'100 asientos pendientes de conciliación o que el saldo '
                  u'del debe sea igual al haber y no están conciliadas. '
                  u'Para solucionar estos problemas se deben verificar los '
                  u'asientos pendientes por conciliar de cada cuenta y '
                  u'conciliarlos (si procede) o en ciertos casos se puede '
                  u'"Desmarcar" la cuenta como conciliable.',
        }
    res['data'].append((
        u'Código', u'Cuenta', u'Apuntes', u'Debe', u'Haber'))
    sql = '''
        select aa.code, aa.name, count(mv.id) as moves,
               sum(mv.debit) as debit, sum(mv.credit) as credit
        from account_move_line mv
        left join account_account aa on mv.account_id = aa.id
        where aa.reconcile = True and mv.reconcile_id is null
        group by aa.code, aa.name
        having count(mv.id) > 100 or sum(mv.debit) = sum(mv.credit)
        order by aa.code
        '''
    for data in lnk.execute_sql(sql):
        # ~ print data
        res['data'].append((
            data[0].decode('utf-8'),
            data[1].decode('utf-8'),
            data[2],
            float(data[3]),
            float(data[4])))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def audit_sso_acounts_moves(context):
    """
    Check relation between employes and company paiments, must be +- 0.37
    """
    res = {
        'name': u'Relación de aportes SSO, empleado/patronales = 0,37 +-2%',
        'group': 'account',
        'data': [],
        'detail': u'La relacion resultante de dividir los saldos mensuales '
                  u'de las cuentas 2130200001 / 2150200001 debe ser de 0.37.',
        }
    accounts = ('2130200001', '2150200001',  # P/E , P/P
                )
    audit_get_trial_balance(context)
    res['data'].append((
        u'Período', u'P/Empleado', u'P/Patronál', u'Relación'))
    values = {}
    # First, load account balance
    for period in context.get('account_periods', {}).get('periods'):
        if not actual_period(period):
            values[period['id']] = {'period': period.get('code', '')}
            for acc in accounts:
                acc_id = get_account_id(acc)
                # ~ Poner saldos en diccionario y luego dividir
                balance = get_trial_balance_account(
                    context, period['id'], acc_id)
                values[period['id']][acc] = balance.get('balance', 0)
    # Then compute and show relation
    for period in context.get('account_periods', {}).get('periods'):
        if values.get(period['id']):
            data = values[period['id']]
            relation = data.get('2150200001', 0) / data.get('2130200001', 1)
            if relation < 0.3626 or relation > 0.3774:
                res['data'].append((
                    data.get('period'),
                    data.get('2150200001'),
                    data.get('2130200001'),
                    '%.3f' % relation
                    ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_invalid_account_group_balance(context):
    """
    Check that the balances of the different account groups do not have an
    invalid balance
    """
    res = {
        'name': u'Grupos de cuentas con saldo inválido',
        'group': 'account',
        'data': [],
        'detail': u'Chequea que los saldos de los distintos grupos de cuentas '
                  u'no tengan saldo invalido. Generalmente se trata de '
                  u'inventarios con signo negativo por aplicación de consumo '
                  u'en exceso',
        }
    audit_get_trial_balance(context)
    res['data'].append((
        u'Período', u'Cuentas', u'Saldo'))
    acc_groups = [
        ('1121000100', '1121000110', '1121000111', '1121000180'),
        ('1121500110', '1121500180'),
        ('1121500210', '1121500280'),
        ('1121500310', '1121500380'),
        ('1121500410', '1121500480'),
        ('1121500510', '1121500580'),
        ('1122000110', '1122000180', '1122000182'),
        ('1123000100', '1123000180', '1123000210', '1123000220', '1123000230'),
        ('1125000100', '1125000180', '1125000210', '1125000220', '1125000230'),
        ]
    for period in context.get('account_periods', {}).get('periods'):
        for grp in acc_groups:
            acc_bal = 0
            accounts = []
            for acc in grp:
                acc_id = get_account_id(acc)
                # ~ Poner saldos en diccionario y luego dividir
                balance = get_trial_balance_account(
                    context, period['id'], acc_id)
                acc_bal += balance.get('balance')
                accounts.append(balance.get('acc_name'))
            if acc_bal < 0:
                res['data'].append((
                    period.get('code') or '',
                    '<br>'.join(accounts) + '<hl>',
                    acc_bal
                    ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_fiscal_book_stocks_period(context):
    #~ date_start = context.get('date_start')
    #~ date_end = context.get('date_end')
    res = {
        'name': u'Libros fiscales por períodos',
        'group': 'account',
        'data': [],
        'detail': u'Validar existencias de libros fiscales por periodo ',
        'start': time.time(),
        }
    audit_get_periods(context)
    books = [
        {'res_model': 'fiscal.book',
         'search_args': ('type', '=', 'purchase'),
         'name': u'Libro de Compras',
         },
        {'res_model': 'fiscal.book',
         'search_args': ('type', '=', 'sale'),
         'name': u'Libro de Ventas',
         },
        {'res_model': 'tcv.stock.book',
         'search_args': None,
         'name': u'Libro de Inventario',
         },
        {'res_model': 'fiscal.summary',
         'search_args': None,
         'name': u'Resumen Fiscal para la Declaración',
         },
        ]
    res['data'].append((u'Período', u'Libro', u'Observaciones'))
    for period in context.get('account_periods', {}).get('periods'):
        if not actual_period(period):
            for book in books:
                search_args = [('period_id', '=', period.get('id'))]
                if book['search_args']:
                    search_args.append(book['search_args'])
                book_id = lnk.execute(
                    book['res_model'], 'search', search_args)
                if not book_id:
                    res['data'].append((
                        period['name'],
                        book['name'],
                        u'No existe registro para el período'
                        ))
                else:
                    fbook = lnk.execute(
                        book['res_model'], 'read', book_id[0],
                        ['state'])
                    if fbook['state'] != 'done':
                        res['data'].append((
                            period['name'],
                            book['name'],
                            u'El libro no está marcado como listo'
                            ))

    if len(res['data']) == 1:
        res['data'] = []
    return res


def invoices_unpaids_balance_0(context):
    res = {
        'name': u'Facturas inpagadas con Saldo 0',
        'group': 'account',
        'data': [],
        'detail': u'Validar facturas inpagadas con saldo 0 o residual '
                  u'(menor a 10,00)',
        'start': time.time(),
        }
    res['data'].append((
        u'Número Factura',
        u'Fecha',
        u'Tipo',
        u'Proveedor/Cliente',
        u'Saldo',
        u'Observaciones',
        ))
    invoice_ids = lnk.execute(
        'account.invoice', 'search', [
            ('state', '=', 'open'),
            ('date_invoice', '>=', context['date_start']),
            ('date_invoice', '<=', context['date_end']),
            ])
    invoice = lnk.execute(
        'account.invoice', 'read', invoice_ids,
        ['number', 'date_invoice', 'partner_id', 'residual', 'type'])
    inv_types = {
        'in_invoice': u'Fct compra',
        'out_invoice': u'Fct Venta',
        'in_refund': u'N/C compra',
        'out_refund': u'N/C compra',
        }
    for inv in invoice:
        if inv['residual'] < 10.0:
            res['data'].append((
                inv['number'],
                inv['date_invoice'],
                inv_types.get(inv['type'], 'Otro'),
                inv['partner_id'][1],
                inv['residual'],
                u'Facturas saldo residual' if inv['residual'] != 0.0 else
                u'Facturas inpagadas con saldo 0'
                ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


def check_total_vat(context):
    res = {
        'name': u'Valor líneas de Libros del IVA',
        'group': 'account',
        'data': [],
        'detail': u'Veifica si existen inconsistencias en el detalle de los libros de compras y ventas',
        'start': time.time(),
        }
    res['data'].append((
        u'Período',
        u'Libro',
        u'Línea',
        u'Fecha',
        u'Nro. Factura',
        u'Proveedor/Cliente',
        u'Diferencia',
        ))
    audit_get_periods(context)
    books = [
        {'res_model': 'fiscal.book',
         'search_args': ('type', '=', 'purchase'),
         'name': u'Libro de Compras',
         },
        {'res_model': 'fiscal.book',
         'search_args': ('type', '=', 'sale'),
         'name': u'Libro de Ventas',
         },
        ]
    for period in context.get('account_periods', {}).get('periods'):
        if not actual_period(period):
            for book in books:
                search_args = [('period_id', '=', period.get('id')),
                               book['search_args']]
                book_id = lnk.execute(
                    book['res_model'], 'search', search_args)
                fbook = lnk.execute(
                    book['res_model'], 'read', book_id, ['fbl_ids'])
                if book and fbook[0].get('fbl_ids'):
                    book_lines = lnk.execute(
                        'fiscal.book.line', 'read', fbook[0]['fbl_ids'], [
                            'rank', 'emission_date', 'invoice_number',
                            'partner_name', 'check_total'])
                for line in book_lines:
                    if line['check_total'] != 0.0:
                        res['data'].append((
                            period['name'],
                            book['name'],
                            line['rank'],
                            line['emission_date'],
                            line['invoice_number'],
                            line['partner_name'],
                            line['check_total'],
                            ))
    if len(res['data']) == 1:
        res['data'] = []
    return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
