"""Create elytras.fr when PayPal rows or Elytras categories exist, then drop paypal

Revision ID: seed_elytras_business
Revises: add_business
Create Date: 2026-11-19 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'seed_elytras_business'
down_revision = 'add_business'
branch_labels = None
depends_on = None

ELYTRAS_NAME = 'elytras.fr'
SALES_NAME = 'Ventes Elytras'
EXPENSE_NAME = 'Dépenses Elytras'


def _category_id(conn, name):
    row = conn.execute(
        sa.text("SELECT id FROM category WHERE name = :name"),
        {"name": name},
    ).first()
    return row[0] if row else None


def _ensure_category(conn, name, type_, icon, color):
    existing = _category_id(conn, name)
    if existing:
        return existing
    conn.execute(
        sa.text(
            """
            INSERT INTO category (name, type, color, icon)
            VALUES (:name, :type, :color, :icon)
            """
        ),
        {"name": name, "type": type_, "color": color, "icon": icon},
    )
    return _category_id(conn, name)


def upgrade():
    conn = op.get_bind()
    has_paypal = conn.execute(
        sa.text("SELECT 1 FROM transaction WHERE paypal IS TRUE LIMIT 1")
    ).first()
    sales_id = _category_id(conn, SALES_NAME)
    expense_id = _category_id(conn, EXPENSE_NAME)

    if has_paypal or sales_id or expense_id:
        already = conn.execute(
            sa.text("SELECT 1 FROM business WHERE name = :name"),
            {"name": ELYTRAS_NAME},
        ).first()
        if already is None:
            sales_id = _ensure_category(conn, SALES_NAME, 0, "🐜", "#b0ea70")
            expense_id = _ensure_category(conn, EXPENSE_NAME, 2, "🐜", "#dfff2a")
            conn.execute(
                sa.text(
                    """
                    INSERT INTO business (
                        name, started_on, opening_result,
                        sales_category_id, expense_category_id
                    )
                    VALUES (
                        :name, :started_on, :opening_result,
                        :sales_id, :expense_id
                    )
                    """
                ),
                {
                    "name": ELYTRAS_NAME,
                    "started_on": "2022-04-01",
                    "opening_result": -20.33,
                    "sales_id": sales_id,
                    "expense_id": expense_id,
                },
            )

    op.drop_column('transaction', 'paypal')


def downgrade():
    op.add_column(
        'transaction',
        sa.Column('paypal', sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM business WHERE name = :name"),
        {"name": ELYTRAS_NAME},
    )
