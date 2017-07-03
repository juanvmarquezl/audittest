# -*- encoding: utf-8 -*-
import openerp_link as lnk
import time


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



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
