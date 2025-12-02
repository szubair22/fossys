"""Add membership and finance tables for OrgSuite

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

This migration adds the following tables for OrgSuite modules:

Membership module:
- members: Organization member tracking
- contacts: Third-party entities (donors, vendors, sponsors)

Finance module:
- accounts: Chart of accounts for double-entry bookkeeping
- journal_entries: Journal entry headers
- journal_lines: Journal entry lines with debits/credits
- donations: Donation tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # MEMBERSHIP MODULE
    # =========================================================================

    # Create enums
    memberstatus = postgresql.ENUM('active', 'inactive', 'pending', 'alumni', 'guest', 'honorary', 'suspended', name='memberstatus', create_type=False)
    membertype = postgresql.ENUM('regular', 'associate', 'lifetime', 'student', 'board', 'volunteer', 'staff', name='membertype', create_type=False)
    contacttype = postgresql.ENUM('donor', 'vendor', 'sponsor', 'partner', 'client', 'volunteer', 'prospect', 'grant_maker', 'government', 'other', name='contacttype', create_type=False)

    # Create the enum types first
    memberstatus.create(op.get_bind(), checkfirst=True)
    membertype.create(op.get_bind(), checkfirst=True)
    contacttype.create(op.get_bind(), checkfirst=True)

    # Members table
    op.create_table(
        'members',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('status', memberstatus, nullable=False, server_default='pending', index=True),
        sa.Column('member_type', membertype, nullable=True, server_default='regular'),
        sa.Column('join_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('member_number', sa.String(50), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('company', sa.String(200), nullable=True),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('contact_type', contacttype, nullable=False, server_default='other', index=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', index=True),
        sa.Column('tax_id', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # =========================================================================
    # FINANCE MODULE
    # =========================================================================

    # Create enums
    accounttype = postgresql.ENUM('asset', 'liability', 'equity', 'income', 'expense', name='accounttype', create_type=False)
    accountsubtype = postgresql.ENUM(
        'cash', 'bank', 'accounts_receivable', 'inventory', 'fixed_asset', 'other_asset',
        'accounts_payable', 'credit_card', 'current_liability', 'long_term_liability',
        'retained_earnings', 'opening_balance', 'other_equity',
        'operating_income', 'donations', 'dues', 'grants', 'other_income',
        'operating_expense', 'cost_of_goods', 'payroll', 'other_expense',
        name='accountsubtype', create_type=False
    )
    journalentrystatus = postgresql.ENUM('draft', 'posted', 'voided', name='journalentrystatus', create_type=False)
    donationstatus = postgresql.ENUM('pledged', 'pending', 'received', 'cancelled', 'refunded', name='donationstatus', create_type=False)
    paymentmethod = postgresql.ENUM('cash', 'check', 'credit_card', 'bank_transfer', 'paypal', 'venmo', 'other', name='paymentmethod', create_type=False)

    # Create the enum types
    accounttype.create(op.get_bind(), checkfirst=True)
    accountsubtype.create(op.get_bind(), checkfirst=True)
    journalentrystatus.create(op.get_bind(), checkfirst=True)
    donationstatus.create(op.get_bind(), checkfirst=True)
    paymentmethod.create(op.get_bind(), checkfirst=True)

    # Accounts (Chart of Accounts) table
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('code', sa.String(20), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('account_type', accounttype, nullable=False, index=True),
        sa.Column('account_subtype', accountsubtype, nullable=True),
        sa.Column('parent_id', sa.String(15), sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true', index=True),
        sa.Column('is_system', sa.Boolean(), server_default='false'),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
        # Unique constraint on org + code
        sa.UniqueConstraint('organization_id', 'code', name='uq_accounts_org_code'),
    )

    # Journal Entries table
    op.create_table(
        'journal_entries',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('entry_number', sa.String(50), nullable=True, index=True),
        sa.Column('entry_date', sa.Date(), nullable=False, index=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_id', sa.String(15), nullable=True),
        sa.Column('status', journalentrystatus, nullable=False, server_default='draft', index=True),
        sa.Column('posted_at', sa.Date(), nullable=True),
        sa.Column('posted_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('voided_at', sa.Date(), nullable=True),
        sa.Column('voided_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('void_reason', sa.String(500), nullable=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Journal Lines table
    op.create_table(
        'journal_lines',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('journal_entry_id', sa.String(15), sa.ForeignKey('journal_entries.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('line_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('account_id', sa.String(15), sa.ForeignKey('accounts.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('debit', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('credit', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('description', sa.String(500), nullable=True),
        # Dimension placeholders for future Intacct-like functionality
        sa.Column('department_id', sa.String(15), nullable=True, index=True),
        sa.Column('project_id', sa.String(15), nullable=True, index=True),
        sa.Column('class_id', sa.String(15), nullable=True, index=True),
        sa.Column('location_id', sa.String(15), nullable=True, index=True),
        sa.Column('custom_dimensions', sa.JSON(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Donations table
    op.create_table(
        'donations',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('member_id', sa.String(15), sa.ForeignKey('members.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('contact_id', sa.String(15), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('donor_name', sa.String(200), nullable=True),
        sa.Column('donor_email', sa.String(255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(3), server_default='USD', nullable=False),
        sa.Column('donation_date', sa.Date(), nullable=False),
        sa.Column('payment_method', paymentmethod, nullable=True),
        sa.Column('payment_reference', sa.String(100), nullable=True),
        sa.Column('status', donationstatus, nullable=False, server_default='pending', index=True),
        sa.Column('purpose', sa.String(200), nullable=True),
        sa.Column('campaign', sa.String(200), nullable=True),
        sa.Column('is_tax_deductible', sa.Boolean(), server_default='true'),
        sa.Column('receipt_number', sa.String(50), nullable=True),
        sa.Column('receipt_sent', sa.Boolean(), server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('donations')
    op.drop_table('journal_lines')
    op.drop_table('journal_entries')
    op.drop_table('accounts')
    op.drop_table('contacts')
    op.drop_table('members')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentmethod')
    op.execute('DROP TYPE IF EXISTS donationstatus')
    op.execute('DROP TYPE IF EXISTS journalentrystatus')
    op.execute('DROP TYPE IF EXISTS accountsubtype')
    op.execute('DROP TYPE IF EXISTS accounttype')
    op.execute('DROP TYPE IF EXISTS contacttype')
    op.execute('DROP TYPE IF EXISTS membertype')
    op.execute('DROP TYPE IF EXISTS memberstatus')
