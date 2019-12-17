# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import base64
import datetime as dt
import encodings.hex_codec
import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal

from trytond.i18n import gettext
from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.url import HOSTNAME
from trytond.report import Report
from trytond.wizard import Wizard, StateAction

from .exceptions import BadHMACError

VERSION = '3.0'
CHECKOUT_URL_TEST = "https://p.monetico-services.com/test/paiement.cgi"
CHECKOUT_URL = "https://p.monetico-services.com/paiement.cgi"
FORM_FIELDS = {
    '3dsdebrayable',
    'TPE',
    'ThreeDSecureChallenge',
    'aliascb',
    'contexte_commande',
    'date',
    'desactivemoyenpaiement',
    'forcesaisiecb',
    'lgue',
    'libelleMonetique',
    'libelleMonetiqueLocalite',
    'mail',
    'montant',
    'protocole',
    'reference',
    'societe',
    'texte-libre',
    'url_retour_err',
    'url_retour_ok',
    'version',
    }
logger = logging.getLogger(__name__)


def _monetico_fromhex(security_key):
    # Use monetico's implementation of bytes.fromhex because their test
    # security key contains non-hexadecimal numbers
    hexStrKey = security_key[0:38]
    hexFinal = security_key[38:40] + "00"
    cca0 = ord(hexFinal[0:1])
    if cca0 > 70 and cca0 < 97:
        hexStrKey += chr(cca0 - 23) + hexFinal[1:2]
    elif hexFinal[1:2] == "M":
        hexStrKey += hexFinal[0:1] + "0"
    else:
        hexStrKey += hexFinal[0:2]
    c = encodings.hex_codec.Codec()
    return c.decode(hexStrKey)[0]


def monetico_sign(security_key, form):
    components = []
    for key in sorted(form):
        if key not in FORM_FIELDS:
            continue
        components.append(b'%s=%s' % (
                key.encode('ascii'), form[key].encode('utf8')))
    signature = hmac.new(
        _monetico_fromhex(security_key), b'*'.join(components), hashlib.sha1)
    return signature.hexdigest()


class Journal(metaclass=PoolMeta):
    __name__ = 'account.payment.journal'

    monetico_account = fields.Many2One(
        'account.payment.monetico.account', "Account", ondelete='RESTRICT',
        states={
            'required': Eval('process_method') == 'monetico',
            'invisible': Eval('process_method') != 'monetico',
            },
        depends=['process_method'])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        monetico_method = ('monetico', 'Monetico')
        if monetico_method not in cls.process_method.selection:
            cls.process_method.selection.append(monetico_method)


class Group(metaclass=PoolMeta):
    __name__ = 'account.payment.group'

    def process_monetico(self):
        pass


class Payment(metaclass=PoolMeta):
    __name__ = 'account.payment'

    monetico_checkout_id = fields.Char("Monetico Checkout ID", readonly=True)
    monetico_account = fields.Function(fields.Many2One(
            'account.payment.monetico.account', "Monetico Account"),
        'on_change_with_monetico_account')
    monetico_order_ctx = fields.Function(
        fields.Char("Monetico Order Context"), 'get_monetico_order_ctx')
    monetico_order_date = fields.Date("Monetico Order Date", readonly=True)
    monetico_authorized_amount = fields.Numeric(
        "Monetico Authorized Amount", digits=(16, Eval('currency_digits', 2)),
        readonly=True, depends=['currency_digits'])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
                'monetico_checkout': {
                    'invisible': ~Eval('state', 'draft').in_(
                        ['approved', 'processing']),
                    'depends': ['state'],
                    },
                })

    @classmethod
    def copy(cls, payments, defaults=None):
        if defaults is None:
            defaults = {}
        defaults.setdefault('monetico_checkout_id', None)
        return super().copy(payments, defaults)

    @fields.depends('journal')
    def on_change_with_monetico_account(self, name=None):
        if self.journal and self.journal.process_method == 'monetico':
            return self.journal.monetico_account.id
        return None

    def _monetico_amount(self, amount):
        return '%s%s' % (self.amount, self.currency.code)

    def _get_monetico_order_ctx(self, party):
        address = party.address_get(type='invoice')
        street_lines = address.street.split('\n')
        return {
            'billing': {
                'addressLine1': street_lines[0],
                'city': address.city,
                'postalCode': address.zip,
                'country': address.country.code,
                },
            }

    def get_monetico_order_ctx(self, name):
        context = self._get_monetico_order_ctx(self.party)
        return base64.b64encode(
            json.dumps(context).encode('utf-8')).decode('utf-8')

    def _monetico_checkout_form(self):
        now = dt.datetime.now()
        form = {
            'TPE': self.monetico_account.tpe_number,
            'contexte_commande': self.monetico_order_ctx,
            'date': now.strftime('%d/%m/%Y:%H:%M:%S'),
            'lgue': 'FR' if not self.party.lang else self.party.lang.code[:2],
            'montant': self._monetico_amount(self.amount),
            'reference': self.monetico_checkout_id,
            'societe': self.monetico_account.company_key,
            'version': VERSION,
            }
        return form

    @property
    def monetico_checkout_form(self):
        form = self._monetico_checkout_form()
        form['MAC'] = monetico_sign(self.monetico_account.security_key, form)
        return form

    @classmethod
    @ModelView.button_action('account_payment_monetico.wizard_checkout')
    def monetico_checkout(cls, payments):
        for payment in payments:
            payment.monetico_checkout_id = uuid.uuid4().hex
        cls.save(payments)


class Account(ModelSQL, ModelView):
    "Monetico Account"
    __name__ = 'account.payment.monetico.account'

    name = fields.Char("Name", required=True)
    testing_account = fields.Boolean("Testing Account")
    security_key = fields.Char("Security Key", required=True)
    company_key = fields.Char("Company Key", required=True)
    tpe_number = fields.Char("TPE Number", required=True)
    form_action = fields.Function(
        fields.Char("Form Action"), 'on_change_with_form_action')

    @classmethod
    def default_testing_account(cls):
        return True

    @fields.depends('testing_account')
    def on_change_with_form_action(self, name=None):
        if not self.testing_account:
            return CHECKOUT_URL
        else:
            return CHECKOUT_URL_TEST

    def webhook(self, form):
        pool = Pool()
        Payment = pool.get('account.payment')

        monetico_mac = form['MAC']
        computed_mac = monetico_sign(self.security_key, form)
        if not hmac.compare_digest(monetico_mac, computed_mac):
            raise BadHMACError(
                gettext('account_payment_monetico.msg_bad_hmac'))

        amount = Decimal(form['montant'])
        try:
            payment, = Payment.seach([
                    ('number', '=', form['reference']),
                    ])
        except ValueError:
            logger.warning("Payment '%s' not found", form['reference'])
            return

        # The amount shouldn't be different but could
        payment.amount = amount

        if form['code-retour'].lower() == 'annulation':
            Payment.fail([payment])
        elif form['code-retour'].lower() in {'payetest', 'paiement'}:
            Payment.succeed([payment])
        else:
            logger.warning("Unknown code-retour '%s' for payment '%s'",
                form['code-retour'], form['reference'])


class Checkout(Wizard):
    "Monetico Checkout"
    __name__ = 'account.payment.monetico.checkout'
    start_state = 'checkout'

    checkout = StateAction('account_payment_monetico.url_checkout')

    def do_checkout(self, action):
        pool = Pool()
        Payment = pool.get('account.payment')

        payment = Payment(Transaction().context['active_id'])
        database = Transaction().database.name
        action['url'] = action['url'] % {
            'hostname': HOSTNAME,
            'database': database,
            'id': payment.monetico_checkout_id,
            }
        return action, {}


class CheckoutPage(Report):
    "Monetico Checkout"
    __name__ = 'account.payment.monetico.checkout'
