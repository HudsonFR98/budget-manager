from datetime import date
from random import Random
from unittest.mock import patch

from budget_manager.lib.const import CONTEXT_VALIDATION
from budget_manager.lib.demo_data import ValidationDemoFiller
from budget_manager.lib.demo_month import (
    DEMO_BUSINESS_EXPENSES_MARKER,
    DEMO_BUSINESS_SALES_MARKER,
    DEMO_SALARY_NOTE,
    DemoMonthBuilder,
)
from budget_manager.lib.task_scheduler import fill_validation_demo_transactions, task_scheduler


def test_month_builder_includes_salary_and_clipped_notes():
    rows = DemoMonthBuilder(Random(1)).build(2027, 3)
    salary = [row for row in rows if row.note == DEMO_SALARY_NOTE]
    assert len(salary) == 1
    assert salary[0].date == date(2027, 3, 1)
    assert salary[0].amount > 0
    assert all(row.note is None or len(row.note) <= 30 for row in rows)
    assert any(row.amount < 0 for row in rows)


def test_month_builder_includes_business_activity_in_june():
    rows = DemoMonthBuilder(Random(1)).build(2027, 6)
    assert any(row.category_name == DEMO_BUSINESS_SALES_MARKER for row in rows)
    assert any(row.category_name == DEMO_BUSINESS_EXPENSES_MARKER for row in rows)
    assert all(row.category_name != "Ventes Elytras" for row in rows)


def test_month_builder_is_deterministic():
    first = DemoMonthBuilder(Random(99)).build(2027, 4)
    second = DemoMonthBuilder(Random(99)).build(2027, 4)
    assert first == second


def test_filler_skips_outside_validation(monkeypatch):
    monkeypatch.setattr("budget_manager.lib.config.CONTEXT", "prod")
    result = ValidationDemoFiller(today=date(2027, 3, 15)).fill_missing_months()
    assert result.startswith("Skipped: not validation")


def test_filler_skips_without_demo_seed(monkeypatch):
    monkeypatch.setattr("budget_manager.lib.config.CONTEXT", CONTEXT_VALIDATION)
    with patch("budget_manager.dao.lock_saving_by_name", return_value=None):
        result = ValidationDemoFiller(today=date(2027, 3, 15)).fill_missing_months()
    assert "seed is not present" in result


def test_scheduled_task_is_registered():
    assert "fill_validation_demo_transactions" in task_scheduler._registered_tasks
    assert task_scheduler._registered_tasks["fill_validation_demo_transactions"] is fill_validation_demo_transactions


def test_months_to_fill_backfills_from_latest_salary(monkeypatch):
    filler = ValidationDemoFiller(today=date(2027, 3, 15))
    monkeypatch.setattr(
        "budget_manager.dao.latest_salary_transaction_date",
        lambda: date(2026, 11, 1),
    )
    months = filler._months_to_fill()
    assert months[0] == (2026, 12)
    assert months[-1] == (2027, 3)


def test_should_close_month_waits_for_leftover_task():
    filler = ValidationDemoFiller(today=date(2027, 1, 1))
    assert filler._should_close_month(2027, 1) is False
    assert filler._should_close_month(2026, 12) is False
    assert filler._should_close_month(2026, 11) is True
    later = ValidationDemoFiller(today=date(2027, 1, 3))
    assert later._should_close_month(2026, 12) is True
