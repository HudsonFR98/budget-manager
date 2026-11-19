"""Seed Base saving

Revision ID: seed_starter_data
Revises: add_app_settings
Create Date: 2026-11-17 11:04:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'seed_starter_data'
down_revision = 'add_app_settings'
branch_labels = None
depends_on = None

SYSTEM_SAVING_NAME = 'Base'
LEGACY_SAVING_NAME = 'Reste'


def upgrade():
    conn = op.get_bind()

    conn.execute(
        sa.text("UPDATE saving SET name = :new_name WHERE name = :old_name"),
        {"new_name": SYSTEM_SAVING_NAME, "old_name": LEGACY_SAVING_NAME},
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO saving (name, note, amount, icon, color, goal, ratio)
            SELECT :name, :note, :amount, :icon, :color, :goal, :ratio
            WHERE NOT EXISTS (SELECT 1 FROM saving WHERE name = :name)
            """
        ),
        {
            "name": SYSTEM_SAVING_NAME,
            "note": "Tout ce qui n'est pas de l'épargne",
            "amount": 0,
            "icon": "🔒",
            "color": "#6ae76b",
            "goal": None,
            "ratio": 1,
        },
    )


def downgrade():
    conn = op.get_bind()

    existing_reste = conn.execute(
        sa.text("SELECT 1 FROM saving WHERE name = :name"),
        {"name": LEGACY_SAVING_NAME},
    ).first()
    if existing_reste is None:
        conn.execute(
            sa.text("UPDATE saving SET name = :old_name WHERE name = :new_name"),
            {"old_name": LEGACY_SAVING_NAME, "new_name": SYSTEM_SAVING_NAME},
        )
