=================================
Account Payment Monetico Scenario
=================================

Imports::

    >>> import os
    >>> import datetime
    >>> from decimal import Decimal
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts

Install account_payment_monetico::

    >>> config = activate_modules('account_payment_monetico')

Create company::

    >>> Company = Model.get('company.company')
    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = create_fiscalyear(company)
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)

Create Monetico account::

    >>> MoneticoAccount = Model.get('account.payment.monetico.account')
    >>> monetico_account = MoneticoAccount(name="Monetico")
    >>> monetico_account.security_key = os.getenv('MONETICO_SECURITY_KEY')
    >>> monetico_account.tpe_number = os.getenv('MONETICO_TPE_NUMBER')
    >>> monetico_account.company_key = os.getenv('MONETICO_COMPANY_KEY')
    >>> monetico_account.testing_account = True
    >>> monetico_account.tpe_kind = 'direct'
    >>> monetico_account.save()

Create webhook identifier::

    >>> monetico_account.click('new_identifier')

Create payment journal::

    >>> PaymentJournal = Model.get('account.payment.journal')
    >>> payment_journal = PaymentJournal(name="Monetico",
    ...     process_method='monetico', monetico_account=monetico_account)
    >>> payment_journal.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create approved payment::

    >>> Payment = Model.get('account.payment')
    >>> payment = Payment()
    >>> payment.journal = payment_journal
    >>> payment.kind = 'receivable'
    >>> payment.party = customer
    >>> payment.amount = Decimal('42')
    >>> payment.description = 'Testing'
    >>> payment.click('approve')
    >>> payment.state
    'approved'

Checkout the payment::

    >>> action_id = payment.click('monetico_checkout')
    >>> checkout = Wizard('account.payment.monetico.checkout', [payment])
    >>> checkout.actions[0].startswith('http')
    True


    >>> bool(payment.monetico_checkout_id)
    True

Process the payment::

    >>> process_payment = Wizard('account.payment.process', [payment])
    >>> process_payment.execute('process')
    >>> payment.state
    'succeeded'
