# -*- coding: utf-8 -*-
# Copyright 2017 - Therp BV (https://therp.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import api, models


class AccountMoveLine(models.Model):

    @api.multi
    def reconcile(
            self, type='auto', writeoff_acc_id=False,
            writeoff_period_id=False, writeoff_journal_id=False):
        """Generate moves to simulate reconciliation over multiple accounts.

        Although in practice this method should not be called for lines from
        multiple partners, assumption is the mother of all ..., so except
        when calling super, we will code as if this can happen.
        """
        # Check wether we have mixed accounts:
        first_account_id = False
        mixed_accounts = False
        for line in self:
            first_account_id = first_account_id or line.account_id.id
            if line.account_id.id != first_account_id:
                mixed_accounts = True
                break
        # If not mixed accounts, nothing special, call super method:
        if not mixed_accounts:
            return super(AccountMoveLine, self).reconcile(
                type=type,
                writeoff_acc_id=writeoff_acc_id,
                writeoff_period_id=writeoff_period_id,
                writeoff_journal_id=writeoff_journal_id
            )
        # We have mixed accounts. Group them by partner and account,
        # determine for each partner wether balance is debit or credit,
        # and wether there are multiple payable or receivable accounts
        # involved. In case there are multiple payable or receivable
        # accounts involved, the balance will be moved to the default
        # payable of receivable account of the partner.
        store = {}
        for line in self:
            partner_id = line.partner_id.id
            if partner_id not in store:
                store[partner_id] = {
                    'debit': 0.0,
                    'credit': 0.0,
                    'payable_account': False,
                    'receivable_account': False,
                }
            partner_store = store[partner_id]
            account_id = line.account_id.id
            if account_id not in partner_store:
                partner_store[account_id] = {
                    'lines': self.browse([]),
                    'debit': 0.0,
                    'credit': 0.0,
                }
            account_store = partner_store[account_id]
            account_store['lines'] = account_store['lines'] | line
            account_store['debit'] += line.debit
            partner_store['debit'] += line.debit
            account_store['credit'] += line.credit
            partner_store['credit'] += line.credit
            if line.account_id.type == 'payable' and \
                    not partner_store['payable_account']:
                partner_store['payable_account'] = line.account_id.id
            if line.account_id.type == 'receivable' and \
                    not partner_store['receivable_account']:
                partner_store['receivable_account'] = line.account_id.id
        # Now create new moves:
        # Find miscelanuous journal for the right company:
        journal_model = self.env['account.journal']
        move_model = self.env['account.move']
        line_model = self.env['account.move.line']
        miscelanuous_journal = journal_model.search([
            ('company_id', '=', self[0].company_id.id),
            ('type', '=', 'general'),
        ])
        for partner_id, partner_store in store.iteritems():
            move = move_model.create({
                'partner_id': partner_id,
                'name': 'Account Reconcile Balancing',
            })
            receivable_account = partner_store['receivable_account']
            payable_account = partner_store['payable_account']
            for account_id, account_store in partner_store.iteritems():
                if account_store['debit'] != account_store['credit'] and \
                   continue
                default_account_id = account_id
                account_type = account_store.lines[0].account_id.type
                if account_type == 'receivable':
                    default_account_id = receivable_account
                else:
                    default_account_id = payable_account
                if account_store['debit'] != account_store['credit'] and \
                        default_account_id != account_id:
                    # Create move lines to balance out this account:
                    difference = \
                        account_store['debit'] - account_store['credit']
                    if difference > 0.0:
                        account_credit = difference
                        default_debit = difference
                        account_debit = 0.0
                        default_credit = 0.0
                    else:
                        account_debit = -difference
                        default_credit = -difference
                        account_credit = 0.0
                        default_debit = 0.0
                    account_line = line.model.create({
                        'move_id': move.id,
                        'partner_id': partner_id,
                        'credit': account_credit,
                        'debit': account_debit,
                        'account_id': account_id,
                    })
                    default_line = line.model.create({
                        'move_id': move.id,
                        'partner_id': partner_id,
                        'credit': default_credit,
                        'debit': default_debit,
                        'account_id': default_account_id,
                    })
                    account_store['lines'] = \
                        account_store['lines'] | account_line
                    default_account_store = partner_store[default_account_id]
                    default_account_store['lines'] = \
                        default_account_store['lines'] | default_line
                    partner_store['credit'] += default_credit
                    partner_store['debit'] += default_debit
            # Now final balancing betwwen account receivable and payable:
            receivable_store = partner_store[receivable_account]
            payable_store = partner_store[payable_account]



        # Now do all reconciles:
        result = False
        for partner_store in store.itervalues():
            for account_store in partner_store.itervalues():
                # We keep only last result:
                result = account_store.lines.reconcile(
                    type=type,
                    writeoff_acc_id=writeoff_acc_id,
                    writeoff_period_id=writeoff_period_id,
                    writeoff_journal_id=writeoff_journal_id
                )
        return result
