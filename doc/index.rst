Account Payment Monetico Module
###############################

The account_payment_stripe module allows to receive payment from `Monetico`_.
It uses the checkout form in the browser.

.. _`Monetico`: https://www.monetico-paiement.fr/

Account
*******

The Account stores the information about the Monetico account like the security
key.

The account's webhook endpoint is the URL used by Monetico webhooks.

Journal
*******

The journal has a new field for the Stripe account.
