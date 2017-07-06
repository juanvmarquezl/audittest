# -*- encoding: utf-8 -*-
import account
import stock
import mrpii
from output_html import export_to_html
import time
from datetime import timedelta
import openerp_link as lnk


results = {
    'account': [],
    'stock': [],
    'mrp': [],
    }

context = {
    'count': 0,
    'date': time.strftime('%d-%m-%Y %H:%M:%S'),
    'date_start': '2017-01-01',
    'date_end': time.strftime('%Y-%m-%d'),
    'database': lnk.db.title(),
    }


def add_test_result(test):
    end = time.time()
    test.update({
        'end': end,
        'elapsed': str(timedelta(seconds=end - test.get('start', end))),
        })
    context['count'] += 1
    print '\ttesting: [%s] %s' % (test.get('group'), test.get('name'))
    if test.get('data'):
        results[test.get('group')].append(test)


print 'Iniciando pruebas de AuditTest...\n'
#~ account
add_test_result(
    account.audit_generic_99999_acounts_moves(context))
add_test_result(
    account.audit_opening_account_periods(context))
add_test_result(
    account.audit_closed_account_period_moves_state(context))

#~ Stock
add_test_result(
    stock.audit_tcv_stock_changes(context))
add_test_result(
    stock.audit_tcv_bunble_status(context))

#~ mrp
add_test_result(
    mrpii.audit_tcv_mrp_gangsaw_picking(context))
add_test_result(
    mrpii.audit_tcv_mrp_finished_slab_picking(context))
add_test_result(
    mrpii.audit_tcv_mrp_waste_slab_state(context))
add_test_result(
    mrpii.audit_tcv_mrp_supplies_picking(context))

print '\nPruebas ejecutadas: %s' % context['count']

export_to_html(results, context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
