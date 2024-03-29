# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import doctest
import os
import unittest


from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import suite as test_suite
from trytond.tests.test_tryton import doctest_teardown
from trytond.tests.test_tryton import doctest_checker


class AccountPaymentMoneticoTestCase(ModuleTestCase):
    'Test Account Payment Monetico module'
    module = 'account_payment_monetico'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            AccountPaymentMoneticoTestCase))
    if (os.getenv('MONETICO_SECURITY_KEY')
            and os.getenv('MONETICO_TPE_NUMBER')
            and os.getenv('MONETICO_COMPANY_KEY')):
        suite.addTests(doctest.DocFileSuite(
                'scenario_account_payment_monetico.rst',
                tearDown=doctest_teardown, encoding='utf-8',
                checker=doctest_checker,
                optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
