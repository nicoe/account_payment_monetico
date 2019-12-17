# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from werkzeug.wrappers import Response

from trytond.pool import Pool
from trytond.protocols.wrappers import with_pool, with_transaction
from trytond.wsgi import app


@app.route('/<database_name>/account_payment_monetico/checkout/<id>')
@with_pool
@with_transaction()
def checkout(request, pool, id):
    pool = Pool()
    Payment = pool.get('account.payment')
    CheckoutPage = pool.get('account.payment.monetico.checkout', type='report')

    payment, = Payment.search([('monetico_checkout_id', '=', id)])
    ext, content, _, _ = CheckoutPage.execute([payment.id], {})
    assert ext == 'html'
    return Response(content, 200, content_type='text/html')
