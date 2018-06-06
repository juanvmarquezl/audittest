# -*- encoding: utf-8 -*-
import sale
import purchase
import stock
import mrpii
import account
from output_html import export_to_html
import time
from datetime import timedelta
import openerp_link as lnk
import sys
import json


results = {
    'sale': [],
    'purchase': [],
    'stock': [],
    'mrp': [],
    'account': [],
    }

context = {
    'count': 0,
    'date': time.strftime('%d-%m-%Y %H:%M:%S'),
    'date_start': '2017-01-01',
    'date_end': time.strftime('%Y-%m-%d'),
    'database': lnk.db.title(),
    }


def add_test_result(audittest, context):
    print '\tTesting: %s...' % (audittest.__name__),
    sys.stdout.flush()
    start = time.time()
    test = audittest(context)
    end = time.time()
    test.update({
        'test_name': audittest.__name__,
        'start': start,
        'end': end,
        'elapsed': str(timedelta(seconds=end - start)),
        })
    with open('./results/%s.json' % test['test_name'], 'w') as outfile:
        json.dump(test, outfile)
    context['count'] += 1
    print 'Done.'
    if test.get('data'):
        results[test.get('group')].append(test)

print 'Iniciando pruebas de AuditTest...\n'

# Sale
#~ add_test_result(
    #~ sale.audit_sale_order_state, context)

# Purchase
#~ add_test_result(
    #~ purchase.audit_purchase_order_state, context)

# Stock
#~ add_test_result(
    #~ stock.audit_tcv_stock_changes, context)
#~ add_test_result(
    #~ stock.audit_tcv_bundle_status, context)
#~ add_test_result(
    #~ stock.check_steel_grit_bags_25, context)
#~ add_test_result(
    #~ stock.check_first_stock_move_no_internal, context)
#~ add_test_result(
    #~ stock.stock_move_granalla, context)
add_test_result(
    stock.stock_move_cient_lot, context)


# mrp
#~ add_test_result(
    #~ stock.check_blocks_stock, context)
#~ add_test_result(
    #~ mrpii.audit_tcv_mrp_gangsaw_picking, context)
#~ add_test_result(
    #~ mrpii.audit_tcv_mrp_finished_slab_picking, context)
#~ add_test_result(
    #~ mrpii.audit_tcv_mrp_waste_slab_state, context)
#~ add_test_result(
    #~ mrpii.audit_tcv_mrp_supplies_picking, context)

# account
#~ add_test_result(
    #~ account.audit_generic_99999_acounts_moves, context)
#~ add_test_result(
    #~ account.audit_opening_account_periods, context)
#~ add_test_result(
    #~ account.audit_closed_account_period_moves_state, context)
#~ add_test_result(
    #~ account.check_imex_purchase_orders, context)
#~ add_test_result(
    #~ account.check_document_sequences, context)
#~ add_test_result(
    #~ account.check_customs_form_state, context)
#~ add_test_result(
    #~ account.check_zero_balance_accounts, context)
#~ add_test_result(
    #~ account.check_move_in_period_accounts, context)
#~ add_test_result(
    #~ account.check_invalid_account_balance, context)
#~ add_test_result(
    #~ account.check_reconcile_status, context)
#~ add_test_result(
    #~ account.audit_sso_acounts_moves, context)
#~ add_test_result(
    #~ account.check_fiscal_book_stocks_period, context)
#~ add_test_result(
    #~ account.check_invalid_account_group_balance, context)
#~ add_test_result(
    #~ account.invoices_unpaids_balance_0, context)
#~ add_test_result(
    #~ account.check_total_vat, context)
#~ add_test_result(
    #~ account.check_inventory_lines_on_error, context)

print '\nPruebas ejecutadas: %s' % context['count']

export_to_html(results, context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
