"""Seed Base saving and Elytras categories

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

    categories = (
        {
            "name": "Ventes Elytras",
            "type": 0,
            "icon": "🐜",
            "color": "#b0ea70",
        },
        {
            "name": "Dépenses Elytras",
            "type": 2,
            "icon": "🐜",
            "color": "#dfff2a",
        },
    )
    for category in categories:
        conn.execute(
            sa.text(
                """
                INSERT INTO category (name, type, color, icon)
                SELECT :name, :type, :color, :icon
                WHERE NOT EXISTS (SELECT 1 FROM category WHERE name = :name)
                """
            ),
            category,
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

    for name in ("Ventes Elytras", "Dépenses Elytras"):
        referenced = conn.execute(
            sa.text(
                """
                SELECT 1 FROM transaction
                WHERE category_id IN (SELECT id FROM category WHERE name = :name)
                LIMIT 1
                """
            ),
            {"name": name},
        ).first()
        if referenced is None:
            conn.execute(
                sa.text("DELETE FROM category WHERE name = :name"),
                {"name": name},
            )
