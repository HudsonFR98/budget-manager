"""Add saving history table

Revision ID: ef12d34567ab
Revises: abcd1234efgh
Create Date: 2025-11-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef12d34567ab'
down_revision = 'abcd1234efgh'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saving_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('saving_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['saving_id'], ['saving.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_saving_history_saving_id', 'saving_history', ['saving_id'])
    op.create_index('ix_saving_history_date', 'saving_history', ['date'])
    op.create_unique_constraint('uq_saving_history_saving_date', 'saving_history', ['saving_id', 'date'])


def downgrade():
    op.drop_constraint('uq_saving_history_saving_date', 'saving_history', type_='unique')
    op.drop_index('ix_saving_history_date', table_name='saving_history')
    op.drop_index('ix_saving_history_saving_id', table_name='saving_history')
    op.drop_table('saving_history')


