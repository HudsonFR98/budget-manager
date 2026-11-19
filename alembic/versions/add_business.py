"""Add business table and widen category names

Revision ID: add_business
Revises: seed_starter_data
Create Date: 2026-11-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_business'
down_revision = 'seed_starter_data'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'category',
        'name',
        existing_type=sa.String(length=30),
        type_=sa.String(length=80),
        existing_nullable=False,
    )
    op.create_table(
        'business',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=70), nullable=False),
        sa.Column('started_on', sa.Date(), nullable=False),
        sa.Column('opening_result', sa.Numeric(precision=8, scale=2), nullable=False, server_default='0'),
        sa.Column('sales_category_id', sa.Integer(), nullable=False),
        sa.Column('expense_category_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['sales_category_id'], ['category.id']),
        sa.ForeignKeyConstraint(['expense_category_id'], ['category.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('sales_category_id'),
        sa.UniqueConstraint('expense_category_id'),
    )


def downgrade():
    op.drop_table('business')
    op.alter_column(
        'category',
        'name',
        existing_type=sa.String(length=80),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
