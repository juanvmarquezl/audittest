# -*- encoding: utf-8 -*-
# this script connect to openerp v6.0 server (XMLRPC)

import xmlrpclib
import time
import psycopg2
import json

#~ Use this lines to create a data.sec file with security params

#~ base = {
#~    'directory': '/home/jmarquez/instancias/produccion/migration_data/data/',
#~    'host': "server ip addrs",
#~    'port': "database port",
#~    'dbname': 'database name',
#~    'operp_user': 'openerp user',
#~    'operp_pwrd': 'openerp password',
#~    'db_user': 'postgresql user',
#~    'db_pwrd': 'postgresql password',
#~    }

#~ with open('data.sec', 'w') as outfile:
#~     json.dump(base, outfile)

with open('data.sec') as data_file:
    dbase = json.load(data_file)


directory = dbase.get('directory')
host = dbase.get('host')
port = dbase.get('port')
db = dbase.get('dbname')
user = dbase.get('operp_user')
pwrd = dbase.get('operp_pwrd')

print 'Conectando al Host: %s, DB: %s...' % (host, db)
seg = 2
print 'Retrazando el inicio de ejecución %s seg' % seg
time.sleep(seg)
#~ #~
#~ #~
url = "http://%s:%s/xmlrpc/" % (host, port)
print url
common_proxy = xmlrpclib.ServerProxy(url + "common")
object_proxy = xmlrpclib.ServerProxy(url + "object")
#~ #~
uid = common_proxy.login(db, user, pwrd)

print 'Conectado\n'


def execute(*args):
    res = False
    try:
        res = object_proxy.execute(db, uid, pwrd, *args)
    except xmlrpclib.Fault as err:
        print u'Exception!'
        print err.faultCode     # the exception instance
        print err.faultString      # arguments stored in .args
        raise SystemExit(0)
    return res


def search_product_id(default_code):
    res = execute('product.product', 'search',
                  [('default_code', '=', default_code)])
    if res and len(res) == 1:
        return res[0]
    print 'Producto no encontrado: %s' % default_code
    return False


def search_partner_id(name):
    res = execute('res.partner', 'search',
                  [('name', '=', name)])
    if res:
        return res[0]
    print 'Partner no encontrado: %s' % name
    return False


def execute_sql(sql, params=None):
    conn_string = "host=%(host) dbname=%(dbname)s " + \
                  "user=%(db_user)s password=%(db_pwrd)s" % dbase
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    if params:
        cursor.execute(sql % params)
    else:
        cursor.execute(sql)
    if 'select' in sql.lower():
        return cursor.fetchall()
    elif 'update' in sql.lower() or 'insert' in sql.lower():
        conn.commit()
    return True
