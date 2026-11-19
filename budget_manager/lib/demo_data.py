"""Live filler that keeps the validation demo current as months pass."""
from __future__ import annotations

import calendar
import logging
from datetime import date
from random import Random

from budget_manager.lib.const import CONTEXT_VALIDATION, SYSTEM_SAVING_NAME
from budget_manager.lib.database import DBSession
from budget_manager.lib.demo_month import (
    SENTINEL_SAVING,
    DemoMonthBuilder,
    add_months,
    resolve_demo_category_name,
)

log = logging.getLogger(__name__)

MAX_BACKFILL_MONTHS = 24


class ValidationDemoFiller:
    """Insert randomized demo months that are still missing in validation."""

    def __init__(self, rng: Random | None = None, today: date | None = None):
        self.rng = rng
        self.today = today or date.today()

    def fill_missing_months(self) -> str:
        from budget_manager.lib import config
        from budget_manager import dao

        if config.CONTEXT != CONTEXT_VALIDATION:
            return "Skipped: not validation context"

        sentinel = dao.lock_saving_by_name(SENTINEL_SAVING)
        if sentinel is None:
            return "Skipped: validation demo seed is not present"

        months = self._months_to_fill()
        if not months:
            DBSession.commit()
            return "No missing demo months"

        dao.ensure_demo_business()

        filled: list[str] = []
        for year, month in months:
            if dao.has_salary_transaction(year, month):
                continue
            count = self._insert_month(year, month)
            if self._should_close_month(year, month):
                from budget_manager.blueprints.saving import (
                    distribute_monthly_savings,
                    snapshot_savings_state,
                )
                distribute_monthly_savings(month=month, year=year)
                last_day = calendar.monthrange(year, month)[1]
                snapshot_savings_state(date(year, month, last_day))
            filled.append(f"{year}-{month:02d}:{count}")

        DBSession.commit()
        if not filled:
            return "No missing demo months"
        return "Filled demo months " + ", ".join(filled)

    def _months_to_fill(self) -> list[tuple[int, int]]:
        from budget_manager import dao

        latest = dao.latest_salary_transaction_date()
        if latest is None:
            year, month = self.today.year, self.today.month
        else:
            year, month = add_months(latest.year, latest.month, 1)

        months: list[tuple[int, int]] = []
        while (year, month) <= (self.today.year, self.today.month):
            months.append((year, month))
            if len(months) >= MAX_BACKFILL_MONTHS:
                break
            year, month = add_months(year, month, 1)
        return months

    def _should_close_month(self, year: int, month: int) -> bool:
        if (year, month) == (self.today.year, self.today.month):
            return False
        prev_year, prev_month = add_months(self.today.year, self.today.month, -1)
        if (year, month) == (prev_year, prev_month) and self.today.day < 2:
            return False
        return True

    def _insert_month(self, year: int, month: int) -> int:
        from budget_manager import dao
        from budget_manager.models import Transaction

        business = dao.ensure_demo_business()
        sales_name = business.sales_category.name
        expense_name = business.expense_category.name
        builder = DemoMonthBuilder(self.rng or Random())
        rows = builder.build(year, month)
        inserted = 0
        for row in rows:
            category_name = resolve_demo_category_name(
                row.category_name, sales_name, expense_name
            )
            category = dao.get_category_by_name(category_name)
            if category is None:
                log.warning("Skipping demo transaction: missing category %s", category_name)
                continue
            saving = dao.get_saving_by_name(row.saving_name) if row.saving_name else None
            if row.saving_name and saving is None:
                log.warning("Skipping demo transaction: missing saving %s", row.saving_name)
                continue
            DBSession.add(Transaction(
                date=row.date,
                note=row.note,
                amount=row.amount,
                category_id=category.id,
                saving_id=saving.id if saving else None,
            ))
            self._apply_to_savings(row.amount, category.type, saving)
            inserted += 1
        DBSession.flush()
        return inserted

    def _apply_to_savings(self, amount: float, category_type: int | None, saving) -> None:
        from budget_manager import dao

        if category_type == 0:
            target = saving or dao.get_saving_by_name(SYSTEM_SAVING_NAME)
            if target is None:
                return
            new_amount = float(target.amount) + amount
            if target.goal:
                new_amount = min(new_amount, float(target.goal))
            target.amount = new_amount
            return
        if saving is not None:
            saving.amount = max(0.0, float(saving.amount) - abs(amount))
