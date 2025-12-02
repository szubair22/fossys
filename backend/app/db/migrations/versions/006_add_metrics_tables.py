"""
Add metrics tables: metrics, metric_values

Revision ID: 006
Revises: 005
Create Date: 2024-11-30
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create metrics tables."""

    # Create metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('value_type', sa.Enum('number', 'currency', 'percent', name='metricvaluetype'), nullable=False, default='number'),
        sa.Column('frequency', sa.Enum('daily', 'weekly', 'monthly', 'quarterly', name='metricfrequency'), nullable=False, default='monthly'),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('is_automatic', sa.Boolean, nullable=False, default=False),
        sa.Column('auto_source', sa.String(100), nullable=True),
        sa.Column('target_value', sa.Numeric(18, 2), nullable=True),
        sa.Column('sort_order', sa.Integer, nullable=False, default=0),
        sa.Column('is_archived', sa.Boolean, nullable=False, default=False),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create metric_values table
    op.create_table(
        'metric_values',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('metric_id', sa.String(15), sa.ForeignKey('metrics.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('value', sa.Numeric(18, 2), nullable=False),
        sa.Column('effective_date', sa.Date, nullable=False, index=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create index on metrics for common queries
    op.create_index('ix_metrics_org_archived', 'metrics', ['organization_id', 'is_archived'])
    op.create_index('ix_metric_values_metric_date', 'metric_values', ['metric_id', 'effective_date'])


def downgrade() -> None:
    """Drop metrics tables."""
    # Drop indexes
    op.drop_index('ix_metric_values_metric_date', table_name='metric_values')
    op.drop_index('ix_metrics_org_archived', table_name='metrics')

    # Drop tables in reverse order
    op.drop_table('metric_values')
    op.drop_table('metrics')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS metricfrequency')
    op.execute('DROP TYPE IF EXISTS metricvaluetype')
