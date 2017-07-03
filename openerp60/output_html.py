# -*- encoding: utf-8 -*-
from mako.template import Template


def export_to_html(results, context):
    print '\nCreando infrme de resultados...'
    mytemplate = Template(filename='./templates/results.html')
    html = mytemplate.render(res=results, ctx=context)
    html_file = open('./results/audittest.html', 'w')
    html_file.write(html.encode('utf-8'))
    html_file.close()
    print 'Listo.\n'


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
