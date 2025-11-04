"""Update date columns from String to Date type

Revision ID: update_date_columns
Revises: add_budget_models
Create Date: 2025-01-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_date_columns'
down_revision = 'add_budget_models'
branch_labels = None
depends_on = None


def upgrade():
    # Update budget table date column with explicit cast
    op.execute('ALTER TABLE budget ALTER COLUMN date TYPE date USING date::date')
    
    # Update transaction table date column with explicit cast
    op.execute('ALTER TABLE transaction ALTER COLUMN date TYPE date USING date::date')


def downgrade():
    # Revert budget table date column
    op.execute('ALTER TABLE budget ALTER COLUMN date TYPE varchar(20) USING date::varchar')
    
    # Revert transaction table date column
    op.execute('ALTER TABLE transaction ALTER COLUMN date TYPE varchar(20) USING date::varchar')
