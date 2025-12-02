"""
Add CRM tables: leads, opportunities, activities

Revision ID: 005
Revises: 004
Create Date: 2024-11-29
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create CRM tables."""

    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('contact_name', sa.String(200), nullable=True),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('company', sa.String(200), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('new', 'contacted', 'qualified', 'disqualified', 'converted', name='leadstatus'), nullable=False, default='new', index=True),
        sa.Column('source', sa.Enum('website', 'referral', 'event', 'cold_call', 'advertisement', 'social_media', 'partner', 'other', name='leadsource'), nullable=False, default='other'),
        sa.Column('owner_user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('converted_contact_id', sa.String(15), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('converted_opportunity_id', sa.String(15), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('related_contact_id', sa.String(15), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('related_project_id', sa.String(15), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('stage', sa.Enum('prospecting', 'qualification', 'proposal_made', 'negotiation', 'won', 'lost', name='opportunitystage'), nullable=False, default='prospecting', index=True),
        sa.Column('probability', sa.Integer, nullable=False, default=10),
        sa.Column('expected_close_date', sa.Date, nullable=True),
        sa.Column('actual_close_date', sa.Date, nullable=True),
        sa.Column('source', sa.Enum('cold_call', 'web', 'partner', 'event', 'referral', 'existing_client', 'marketing_campaign', 'other', name='opportunitysource'), nullable=False, default='other'),
        sa.Column('owner_user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('opportunity_id', sa.String(15), sa.ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('contact_id', sa.String(15), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.Enum('call', 'email', 'meeting', 'note', 'task', name='activitytype'), nullable=False, index=True),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add foreign key for converted_opportunity_id in leads
    op.create_foreign_key(
        'fk_leads_converted_opportunity',
        'leads',
        'opportunities',
        ['converted_opportunity_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop CRM tables."""
    # Drop foreign key first
    op.drop_constraint('fk_leads_converted_opportunity', 'leads', type_='foreignkey')

    # Drop tables in reverse order
    op.drop_table('activities')
    op.drop_table('opportunities')
    op.drop_table('leads')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS activitytype')
    op.execute('DROP TYPE IF EXISTS opportunitysource')
    op.execute('DROP TYPE IF EXISTS opportunitystage')
    op.execute('DROP TYPE IF EXISTS leadsource')
    op.execute('DROP TYPE IF EXISTS leadstatus')
