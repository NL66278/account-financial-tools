.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================================
Reconcile debit and credit accounts
===================================

This module provides the possibility to reconcile debit and credit accounts,
or more in general the move lines from different accounts, even if some
of those are of type payable and others of type receivable.

For instance a debit line from a type receivable account can be reconciled
with a credit line from a payable account.

As normal accounting rules prohibit this kind of reconciliation, this is
executed by creating moves on a miscelanuous journal. So everything is
traceable. The actual reconciliations are still within one account.


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-financial-tools/issues>`_.
In case of trouble, please check there if your issue has already been
reported. If you spotted it first, help us smashing it by providing a
detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Ronald Portier, Therp <ronald@therp.nl>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
