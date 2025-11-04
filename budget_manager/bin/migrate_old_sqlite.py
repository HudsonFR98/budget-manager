import argparse
import logging
from datetime import datetime, date
from typing import Iterable, Optional

from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from budget_manager.lib import config as app_config
from budget_manager.lib import database
from budget_manager.models import Category, Budget, Transaction  # type: ignore
from budget_manager.models.category import category_budget  # association table

log = logging.getLogger("migrate_old_sqlite")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def open_sqlite_engine(sqlite_path: str) -> Engine:
    if not sqlite_path.startswith("sqlite:///"):
        url = f"sqlite:///{sqlite_path}"
    else:
        url = sqlite_path
    return create_engine(url)


def parse_date(value: Optional[str]) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except Exception:
            continue
    s = str(value).split(" ")[0]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        log.warning("Unable to parse date '%s', defaulting to today", value)
        return date.today()


def clamp(s: Optional[str], max_len: int = 30) -> Optional[str]:
    if s is None:
        return None
    s = str(s)
    return s if len(s) <= max_len else s[:max_len]


def chunked(iterable: Iterable, size: int):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def set_sequence_to_max(conn, table_name: str, id_col: str = "id"):
    seq_name_row = conn.execute(text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": table_name, "c": id_col}).fetchone()
    if not seq_name_row or not seq_name_row[0]:
        return
    seq_name = seq_name_row[0]
    # Default to 1 when table is empty to avoid setval out-of-bounds
    conn.execute(text(f"SELECT setval(:seq, GREATEST(COALESCE((SELECT MAX({id_col}) FROM {table_name}), 1), 1))"), {"seq": seq_name})


def migrate(sqlite_path: str, dry_run: bool = False, links_only: bool = False):
    engine = database.open(app_config.SQLALCHEMY_DATABASE_URI)
    session: Session = database.DBSession()  # type: ignore

    src_engine = open_sqlite_engine(sqlite_path)
    src_meta = MetaData()
    src_meta.reflect(bind=src_engine, only=["category", "budget", "category_budget", "transaction"])

    t_category: Table = src_meta.tables.get("category")  # type: ignore
    t_budget: Table = src_meta.tables.get("budget")  # type: ignore
    t_cat_budget: Table = src_meta.tables.get("category_budget")  # type: ignore
    t_tx: Table = src_meta.tables.get("transaction")  # type: ignore

    missing = [
        name for name, tbl in (
            ("category", t_category),
            ("budget", t_budget),
            ("category_budget", t_cat_budget),
            ("transaction", t_tx),
        ) if tbl is None
    ]
    if missing:
        raise RuntimeError(f"Missing required tables in SQLite database: {', '.join(missing)}")

    with src_engine.connect() as src_conn, engine.begin() as tgt_conn:
        # Categories
        if not links_only:
            log.info("Migrating categories…")
            rows = src_conn.execute(select(t_category)).mappings().all()
            log.info("Found %d categories", len(rows))
            if not dry_run and rows:
                for batch in chunked(rows, 500):
                    mappings = [{
                        "id": r["id"],
                        "name": clamp(r.get("name"), 30),
                        "type": r.get("type"),
                        "color": clamp(r.get("color"), 30),
                        "icon": clamp(r.get("icon"), 30),
                    } for r in batch]
                    session.bulk_insert_mappings(Category, mappings)
                session.flush()
                set_sequence_to_max(tgt_conn, Category.__tablename__)

        # Budgets
        if not links_only:
            log.info("Migrating budgets…")
            rows = src_conn.execute(select(t_budget)).mappings().all()
            log.info("Found %d budgets", len(rows))
            if not dry_run and rows:
                for batch in chunked(rows, 500):
                    mappings = [{
                        "id": r["id"],
                        "date": parse_date(r.get("date")),
                        "amount": r["amount"],
                    } for r in batch]
                    session.bulk_insert_mappings(Budget, mappings)
                session.flush()
                set_sequence_to_max(tgt_conn, Budget.__tablename__)

        # Category-Budget links
        log.info("Migrating category_budget links…")
        rows = src_conn.execute(select(t_cat_budget)).mappings().all()
        log.info("Found %d links", len(rows))
        if not dry_run and rows:
            # Use session connection to ensure visibility of uncommitted inserts
            # Also filter to existing IDs to avoid FK violations if running links-only independently
            existing_cat_ids = {r[0] for r in session.execute(text("SELECT id FROM category")).fetchall()}
            existing_bud_ids = {r[0] for r in session.execute(text("SELECT id FROM budget")).fetchall()}
            for batch in chunked(rows, 1000):
                values = [
                    {"category_id": r["category_id"], "budget_id": r["budget_id"]}
                    for r in batch
                    if (r["category_id"] in existing_cat_ids and r["budget_id"] in existing_bud_ids)
                ]
                if values:
                    session.execute(category_budget.insert(), values)

        # Transactions
        if not links_only:
            log.info("Migrating transactions…")
            rows = src_conn.execute(select(t_tx)).mappings().all()
            log.info("Found %d transactions", len(rows))
            if not dry_run and rows:
                for batch in chunked(rows, 500):
                    mappings = [{
                        "id": r["id"],
                        "date": parse_date(r.get("date")),
                        "note": clamp(r.get("note"), 30),
                        "amount": r["amount"],
                        "category_id": r["category_id"],
                        "paypal": bool(r.get("paypal")) if r.get("paypal") is not None else False,
                    } for r in batch]
                    session.bulk_insert_mappings(Transaction, mappings)
                session.flush()
                set_sequence_to_max(tgt_conn, Transaction.__tablename__)

        if dry_run:
            log.info("Dry run complete. No changes committed.")
            session.rollback()
        else:
            session.commit()
            log.info("Migration committed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Migrate old budget_previsionnel SQLite DB to new Postgres DB (dev)")
    parser.add_argument("--source", required=True, help="Path to source SQLite .db file (inside container or mounted path)")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes")
    parser.add_argument("--links-only", action="store_true", help="Only migrate category_budget links")
    args = parser.parse_args()

    migrate(sqlite_path=args.source, dry_run=args.dry_run, links_only=args.links_only)


if __name__ == "__main__":
    main()
