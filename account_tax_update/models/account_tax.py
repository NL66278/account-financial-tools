# -*- coding: utf-8 -*-
# Copyright 2012-2018 Therp BV <https://therp.nl>.
# Copyright 2013 Camptocamp SA.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openerp import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def name_get(self):
        if self.env.context.get('tax_real_name', False):
            return [(this.id, this.name) for this in self]
        return super(AccountTax, self).name_get()

    @api.multi
    def duplicate_tax_codes(self):
        """Create new , but not duplicated, tax codes for tax.

        Link new tax codes to tax.
        """
        context = self.env.context
        legacy_prefix = context.get('legacy_prefix', 'legacy')
        tax_code_map = context.get('tax_code_map', {})
        tax_code_fields = [
            'ref_tax_code_id',
            'tax_code_id',
            'ref_base_code_id',
            'base_code_id']
        vals = {}
        for field_name in tax_code_fields:
            old_tax_code = self[field_name]
            if old_tax_code.id not in tax_code_map:
                old_name = old_tax_code.name
                old_tax_code.write({
                    'name': '[%s] %s' % (legacy_prefix, old_tax_code.name)})
                new_tax_code = old_tax_code.copy({'name': old_name})
                tax_code_map[old_tax_code.id] = new_tax_code
            new_tax_code = tax_code_map[old_tax_code.id]
            vals[field_name] = new_tax_code.id
        self.write(vals)

    @api.multi
    def copy(self, default=None):
        """Copy tax, complete with child taxes.

        Optionally duplicate also the tax codes.
        """
        # pylint: disable=arguments-differ
        self.ensure_one()
        default = dict(default or {})
        # pylint: disable=no-value-for-parameter
        vals = self.copy_data(default=default)[0]
        new_tax = super(AccountTax, self).create(vals)
        if self.env.context.get('duplicate_tax_code', False):
            new_tax.duplicate_tax_codes()  # pylint: disable=no-member
        return new_tax
