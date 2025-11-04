"""Add budget management models

Revision ID: add_budget_models
Revises: add_task_tables
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_budget_models'
down_revision = 'add_task_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create budget table
    op.create_table('budget',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create category table
    op.create_table('category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=30), nullable=False),
        sa.Column('type', sa.Integer(), nullable=True),
        sa.Column('color', sa.String(length=30), nullable=True),
        sa.Column('icon', sa.String(length=30), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create transaction table
    op.create_table('transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('note', sa.String(length=30), nullable=True),
        sa.Column('amount', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('paypal', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create category_budget association table
    op.create_table('category_budget',
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('budget_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['budget_id'], ['budget.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
        sa.PrimaryKeyConstraint('category_id', 'budget_id')
    )


def downgrade():
    op.drop_table('category_budget')
    op.drop_table('transaction')
    op.drop_table('category')
    op.drop_table('budget')
