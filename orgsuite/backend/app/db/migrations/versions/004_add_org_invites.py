"""Add org_invites table for invitation-based onboarding

Revision ID: 004
Revises: 003
Create Date: 2025-01-15 00:00:00.000000

This migration adds the org_invites table for managing organization invitations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create org_invites table
    op.create_table(
        'org_invites',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('role', sa.Enum('admin', 'member', 'viewer', name='orginviterole', create_constraint=True), nullable=False, server_default='member'),
        sa.Column('token', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('status', sa.Enum('pending', 'accepted', 'expired', 'cancelled', name='orginvitestatus', create_constraint=True), nullable=False, server_default='pending', index=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('invited_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('accepted_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message', sa.String(500), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('org_invites')
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS orginviterole')
    op.execute('DROP TYPE IF EXISTS orginvitestatus')
