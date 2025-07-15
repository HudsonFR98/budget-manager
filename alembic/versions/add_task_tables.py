"""Add task tables

Revision ID: add_task_tables
Revises: initial_migration
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_task_tables'
down_revision = 'initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Create task_executions table
    op.create_table('task_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_name', sa.String(length=100), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_time', sa.Integer(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('task_args', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('task_kwargs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_executions_task_name'), 'task_executions', ['task_name'], unique=False)
    op.create_index(op.f('ix_task_executions_task_id'), 'task_executions', ['task_id'], unique=False)

    # Create scheduled_tasks table
    op.create_table('scheduled_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_name', sa.String(length=100), nullable=False),
        sa.Column('task_function', sa.String(length=100), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_args', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('task_kwargs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.Column('next_run', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_name')
    )


def downgrade():
    op.drop_index(op.f('ix_task_executions_task_id'), table_name='task_executions')
    op.drop_index(op.f('ix_task_executions_task_name'), table_name='task_executions')
    op.drop_table('task_executions')
    op.drop_table('scheduled_tasks') 