# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool

from . import payment
from . import ir
from . import routes

__all__ = ['register']


def register():
    Pool.register(
        ir.Cron,
        payment.Journal,
        payment.Group,
        payment.Payment,
        payment.Account,
        module='account_payment_monetico', type_='model')
    Pool.register(
        payment.Checkout,
        module='account_payment_monetico', type_='wizard')
    Pool.register(
        payment.CheckoutPage,
        module='account_payment_monetico', type_='report')
