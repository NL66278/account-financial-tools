# -*- coding: utf-8 -*-
# Copyright 2012 Therp BV <https://therp.nl>.
# Copyright 2013 Camptocamp SA.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime

from openerp import _, api, fields, models
from openerp.tools.misc import pickle
from openerp.exceptions import Warning as UserError


class UpdateTaxConfig(models.Model):
    """
    A configuration model to collect taxes to be replaced with
    duplicates, but with a different amount. Once the taxes are
    collected, the following operations can be carried out by
    the user.

    1) generate the target taxes
    2) Update defaults for sales taxes
    3) Update defaults for purchase taxes
    4) Set old taxes inactive
    """
    _name = 'account.update.tax.config'
    _description = 'Update taxes'

    name = fields.Char(
        string='Legacy taxes prefix',
        required=True,
        help="The processed taxes will be marked with this name")
    log = fields.Text(readonly="1")
    purchase_line_ids = fields.One2many(
        'account.update.tax.config.line',
        'purchase_config_id',
        'Purchase taxes')
    sale_line_ids = fields.One2many(
        'account.update.tax.config.line',
        'sale_config_id',
        'Sales taxes')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('update_sales', 'Sales updated'),
            ('update_purchase', 'Purchase updated'),
            ('done', 'Done')],
        string='State',
        default='draft',
        readonly=True)
    default_amount = fields.Float(
        string='Default new amount',
        digits=(14, 4),
        help="Although it is possible to specify a distinct new amount "
             "per tax, you can set the default value here.")
    sale_set_defaults = fields.Boolean(
        string='Sales tax defaults have been set',
        readonly=True)
    purchase_set_defaults = fields.Boolean(
        string='Purchase tax defaults have been set',
        readonly=True)
    sale_set_inactive = fields.Boolean(
        string='Sales taxes have been set to inactive',
        readonly=True)
    purchase_set_inactive = fields.Boolean(
        string='Purchase taxes have been set to inactive',
        readonly=True)
    duplicate_tax_code = fields.Boolean(string='Duplicate Tax code linked')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique.')]

    @api.multi
    def confirm(self):
        """
        Set the configuration to confirmed, so that no new
        taxes can be added. Create the duplicate taxes,
        rename the legacy taxes and recreate the hierarchical
        structure. Construct the fiscal position tax mappings.
        """
        # pylint: disable=too-many-locals,protected-access,too-many-branches
        # pylint: disable=too-many-statements,
        self.ensure_one()
        tax_map = {}
        local_context = self.env.context.copy()
        local_context.update({
            'duplicate_tax_code': self.duplicate_tax_code,
            'legacy_prefix': self.name,
            'tax_code_map': {}})
        log = (self.log or '') + (
            "\n*** %s: Confirmed with the following taxes:\n" %
            datetime.now().ctime())
        for line in self.sale_line_ids + self.purchase_line_ids:
            source_tax = line.source_tax_id
            log += " - %s (%s)\n" % (source_tax.name, source_tax.description)
            # Switch names around, not violating the uniqueness constraint
            tax_old_name = source_tax.name
            tax_old_description = source_tax.description
            source_tax.write({
                'name': '[%s] %s' % (self.name, tax_old_name),
                'description':
                    '[%s] %s' % (self.name, tax_old_description)})
            if source_tax.amount in [1.0, -1.0, 0]:
                amount_new = source_tax.amount
            else:
                amount_new = line.amount_new or \
                    self.default_amount or source_tax.amount
            target_tax = source_tax.with_context(local_context).copy({
                'name': '[new] %s' % tax_old_name,
                'amount': amount_new})
            target_tax.write({
                'name': tax_old_name,
                'description':
                    line.target_tax_description or tax_old_description})
            tax_map[source_tax.id] = target_tax.id
            line.write({'target_tax_id': target_tax.id})
        # Map fiscal positions
        fp_tax_model = self.env['account.fiscal.position.tax']
        fp_taxes = fp_tax_model.search([('tax_src_id', 'in', tax_map.keys())])
        for fp_tax in fp_taxes:
            new_fp_tax = fp_tax.copy({
                'tax_src_id': tax_map[fp_tax.tax_src_id.id],
                'tax_dest_id': tax_map.get(
                    fp_tax.tax_dest_id.id, fp_tax.tax_dest_id.id)})
            log += (
                "\nCreate new tax mapping on position %s:\n"
                "%s (%s)\n"
                "=> %s (%s)\n" % (
                    new_fp_tax.position_id.name,
                    new_fp_tax.tax_src_id.name,
                    new_fp_tax.tax_src_id.description,
                    new_fp_tax.tax_dest_id.name,
                    new_fp_tax.tax_dest_id.description))
        self.write({'state': 'confirm', 'log': log})

    @api.multi
    def set_defaults(self):
        """Set default taxes on products, accounts and maybe other models."""
        # pylint: disable=too-many-locals,protected-access
        self.ensure_one()
        context = self.env.context
        if not context.get('type_tax_use'):
            raise UserError(_("Can not detect tax use type"))
        local_context = context.copy()
        local_context['active_test'] = False
        tax_lines = self['%s_line_ids' % context['type_tax_use']]
        tax_map = dict(
            [(x.source_tax_id.id, x.target_tax_id.id) for x in tax_lines])
        ir_values_model = self.env['ir.values']
        log = (self.log or '') + (
            "\n*** %s: Writing default %s taxes:\n" % (
                datetime.now().ctime(),
                context['type_tax_use']))

        def update_defaults(model_name, field_name, column):
            log = ''
            if column._obj == 'account.tax':
                values = ir_values_model.search([
                    ('key', '=', 'default'),
                    ('model', '=', model_name),
                    ('name', '=', field_name)])
                for value in values:
                    val = False
                    write = False
                    try:
                        # Currently, value_unpickle from ir_values
                        # fails as it feeds unicode to pickle.loads()
                        val = pickle.loads(str(value.value))
                    except Exception:  # pylint: disable=broad-except
                        continue
                    if isinstance(val, (int, long)) and val in tax_map:
                        write = True
                        new_val = tax_map[val]
                    elif isinstance(val, list) and val:
                        new_val = []
                        for i in val:
                            if i in tax_map:
                                write = True
                            new_val.append(tax_map.get(i, i))
                    if write:
                        log += "Default (%s => %s) for %s,%s\n" % (
                            val, new_val, model_name, field_name)
                        value.write({'value_unpickle': new_val})
            return log

        model_model = self.env['ir.model']
        all_models = model_model.search([])
        # 6.1: self.pool.models.items():
        for model in all_models:
            model_name = model.model
            current_model = self.env[model_name]
            for field_name, column in current_model._fields.items():
                log += update_defaults(model_name, field_name, column)
            for field_name, field_tuple in \
                    model._inherit_fields.iteritems():
                if len(field_tuple) >= 3:
                    column = field_tuple[2]
                    log += update_defaults(model_name, field_name, column)

        log += "\nReplacing %s taxes on accounts and products\n" % (
            context['type_tax_use'])
        model_field_map = [
            # make this a configurable list of ir_model_fields one day?
            ('account.account', 'tax_ids'),
            ('product.product', 'supplier_taxes_id'),
            ('product.product', 'taxes_id'),
            ('product.template', 'supplier_taxes_id'),
            ('product.template', 'taxes_id')]
        for model_name, field in model_field_map:
            current_model = self.env[model_name]
            current_records = current_model.search([
                (field, 'in', tax_map.keys())])
            for record in current_records:
                new_val = []
                write = False
                for i in record[field]:
                    if i in tax_map:
                        write = True
                    new_val.append(tax_map.get(i, i))
                if write:
                    record.write({field: [(6, 0, new_val)]})
                    log += "Value (%s => %s) for %s,%s,%s\n" % (
                        record[field],
                        new_val,
                        model_name,
                        field,
                        record['id'])
        self.write({
            'log': log,
            '%s_set_defaults' % context['type_tax_use']: True})
        return {
            'name': self._description,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'domain': [],
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'res_id': self.ids[0],
            'nodestroy': True}

    @api.multi
    def set_inactive(self):
        self.ensure_one()
        context = self.env.context
        if not context.get('type_tax_use'):
            raise UserError(_("Can not detect tax use type"))
        tax_lines = self['%s_line_ids' % context['type_tax_use']]
        tax_model = self.env['account.tax']
        tax_ids = tax_model.search([
            ('id', 'in', [x.source_tax_id.id for x in tax_lines])])
        tax_ids.write({'active': False})
        log = (self.log or '') + (
            "\n*** %s: Setting %s %s taxes inactive\n" % (
                datetime.now().ctime(),
                len(tax_ids),
                context['type_tax_use']))
        self.write({
            'log': log,
            '%s_set_inactive' % context['type_tax_use']: True})
        return {
            'name': self._description,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'domain': [],
            'context': context,
            'type': 'ir.actions.act_window',
            'res_id': self.ids[0],
            'nodestroy': True}


class UpdateTaxConfigLine(models.Model):
    _name = 'account.update.tax.config.line'
    _description = "Tax update configuration lines"
    _rec_name = 'source_tax_id'  # Wha'evuh

    @api.multi
    def _compute_state(self):
        for this in self:
            config = this.sale_config_id or this.purchase_config_id
            if config:
                this.state = config.state

    purchase_config_id = fields.Many2one(
        'account.update.tax.config',
        'Configuration')
    sale_config_id = fields.Many2one(
        'account.update.tax.config',
        'Configuration')
    source_tax_id = fields.Many2one(
        'account.tax', 'Source tax',
        required=True)
    source_tax_description = fields.Char(
        string="Old tax code",
        related='source_tax_id.description',
        readonly=True)
    amount_old = fields.Float(
        string='Old amount',
        related='source_tax_id.amount',
        readonly=True)
    target_tax_id = fields.Many2one(
        'account.tax',
        'Target tax',
        readonly=True)
    target_tax_description = fields.Char(string="New tax code")
    amount_new = fields.Float(string='New amount')
    state = fields.Char(compute='_compute_state')
