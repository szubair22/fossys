"""Add organization_id column to meetings table

Revision ID: 003
Revises: 002
Create Date: 2025-01-15 00:00:00.000000

This migration adds the organization_id column to the meetings table to allow
direct organization linkage for meetings (in addition to optional committee linkage).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add organization_id column to meetings table
    op.add_column(
        'meetings',
        sa.Column(
            'organization_id',
            sa.String(15),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
            nullable=True,  # Nullable for existing/legacy records
            index=True
        )
    )

    # Create index on organization_id
    op.create_index(
        'ix_meetings_organization_id',
        'meetings',
        ['organization_id']
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_meetings_organization_id', table_name='meetings')
    # Drop column
    op.drop_column('meetings', 'organization_id')
