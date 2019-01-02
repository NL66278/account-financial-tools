This module aims at assisting the finance manager with implementing a tax
increase. Currently, only taxes that apply a percentage are covered.

The module creates a new menu item 'Update tax wizard' in the financial
settings menu, under the Taxes submenu. Using the wizard, you can select
the sales and purchase taxes that need to be upgraded and assign a new
percentage.

The selected taxes are in fact duplicated by running the wizard, so that
existing entries in the system are not affected. The new taxes are mapped
automatically in the appropriate fiscal positions. The wizard can replace
default values on accounts and products on demand. Defaults for purchase
and sales taxes can be set at independent times. During the transition,
the old taxes can still be selected manually on invoice lines etc.

You can select to also duplicate linked tax code

After the transition, the old taxes can be made inactive.

This module is compatible with OpenERP 8.0
