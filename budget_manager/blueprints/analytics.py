import json
import math
from datetime import datetime, date, timedelta
from calendar import monthrange
from collections import defaultdict
from statistics import median

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import extract, func, case, or_
from budget_manager.blueprints.saving import calculate_leftover_for_savings, sold, snapshot_savings_state
import budget_manager.dao as dao
import budget_manager.process as process
from budget_manager.models import *
from budget_manager.lib.database import DBSession

analytics = Blueprint("analytics", __name__)

@analytics.route('/', methods=['GET', 'POST'])
@login_required
def summary():
    """Analytics dashboard with savings and spending insights"""
    months_param = request.args.get('months', 6)
    try:
        months_window = max(1, min(24, int(months_param)))
    except ValueError:
        months_window = 6

    plot = process.StackedSpendingChart(months=months_window).generate()

    _ensure_today_saving_snapshots()

    avg_leftover = _average_leftover_amount(months=months_window)
    savings_insights = _build_savings_insights(avg_leftover=avg_leftover, months=months_window)
    balance_metrics = _compute_balance_metrics(months_window)
    income_metrics = _compute_income_metrics(months_window)
    category_stats = _build_category_stats(months_window)

    ctx = {
        'chart': plot,
        'months_window': months_window,
        'avg_leftover': avg_leftover,
        'savings_insights': savings_insights,
        'savings_insights_json': json.dumps(savings_insights),
        'balance_metrics': balance_metrics,
        'income_metrics': income_metrics,
        'category_stats': category_stats,
    }
    return render_template('analytics/summary.html', **ctx)


def _month_start(dt: date) -> date:
    return dt.replace(day=1)


def _month_end(dt: date) -> date:
    return dt.replace(day=monthrange(dt.year, dt.month)[1])


def _shift_month(dt: date, months: int) -> date:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _month_sequence(months: int) -> list[date]:
    today = date.today()
    last_complete_start = _shift_month(_month_start(today), -1)
    start = _shift_month(last_complete_start, -(months - 1))
    sequence = []
    current = start
    for _ in range(months):
        sequence.append(current)
        current = _shift_month(current, 1)
    return sequence


def _ensure_today_saving_snapshots():
    """Capture today's snapshot for each saving if not already stored."""
    snapshot_savings_state(date.today())


def _average_leftover_amount(months: int = 6) -> float:
    total = 0.0
    count = 0
    reference = datetime.now()
    for offset in range(months):
        target = _shift_month(reference, -offset)
        leftover = calculate_leftover_for_savings(month=target.month, year=target.year)
        total += leftover
        count += 1
    return round(total / count, 2) if count else 0.0


def _build_saving_evolution_series(saving: Saving, months: int = 12) -> list[dict]:
    sequence = _month_sequence(months)
    if not sequence:
        return []
    start_date = sequence[0]
    history_rows = SavingHistory.query.filter(
        SavingHistory.saving_id == saving.id,
        SavingHistory.date >= start_date
    ).order_by(SavingHistory.date.asc()).all()
    baseline_entry = SavingHistory.query.filter(
        SavingHistory.saving_id == saving.id,
        SavingHistory.date < start_date
    ).order_by(SavingHistory.date.desc()).first()

    last_amount = float(baseline_entry.amount) if baseline_entry else float(saving.amount)
    idx = 0
    series = []
    for dt in sequence:
        month_end = _month_end(dt)
        while idx < len(history_rows) and history_rows[idx].date <= month_end:
            last_amount = float(history_rows[idx].amount)
            idx += 1
        series.append({
            "label": dt.strftime("%b %Y"),
            "value": round(last_amount, 2)
        })
    return series


def _estimate_goal_date(saving: Saving, avg_leftover: float):
    if not saving.goal:
        return None, None, 0.0
    current_amount = float(saving.amount)
    goal_amount = float(saving.goal)
    if current_amount >= goal_amount:
        return None, 0, 0.0
    ratio = float(saving.ratio or 0.0)
    expected_monthly = avg_leftover * ratio
    if expected_monthly <= 0:
        return None, None, expected_monthly
    remaining = goal_amount - current_amount
    months_needed = math.ceil(remaining / expected_monthly)
    estimated_date = _shift_month(date.today(), months_needed)
    return estimated_date, months_needed, expected_monthly


def _build_savings_insights(avg_leftover: float, months: int = 12) -> list[dict]:
    savings = Saving.query.order_by(Saving.id).all()
    insights = []
    for saving in savings:
        evolution = _build_saving_evolution_series(saving, months=months)
        estimated_date, months_needed, expected_monthly = _estimate_goal_date(saving, avg_leftover)
        insights.append({
            "id": saving.id,
            "name": saving.name,
            "icon": saving.icon,
            "color": saving.color or "#4CAF50",
            "current_amount": round(float(saving.amount), 2),
            "goal": round(float(saving.goal), 2) if saving.goal else None,
            "ratio": float(saving.ratio or 0.0),
            "estimated_goal_date": estimated_date.strftime("%Y-%m") if estimated_date else None,
            "months_to_goal": months_needed,
            "monthly_expected": round(expected_monthly, 2),
            "evolution": evolution
        })
    return insights


def _sum_transactions_until(target_date: date) -> float:
    total = DBSession.query(func.sum(Transaction.amount)).filter(
        (Transaction.paypal == False) | (Transaction.paypal == None),
        Transaction.date <= target_date
    ).scalar()
    return float(total or 0.0)


def _compute_pct_change(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return round(((current - reference) / abs(reference)) * 100, 2)


def _compute_balance_metrics(months: int) -> dict:
    current_balance = float(sold())
    past_cutoff = _month_end(_shift_month(date.today(), -months))
    past_balance = _sum_transactions_until(past_cutoff)
    change_pct = _compute_pct_change(current_balance, past_balance)
    return {
        "current": round(current_balance, 2),
        "reference": round(past_balance, 2),
        "change_pct": change_pct,
        "label": f"vs. {months} months ago",
    }


def _sum_income_between(start_date: date, end_date: date) -> float:
    total = DBSession.query(func.sum(Transaction.amount)).join(Category).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Category.type == 0
    ).scalar()
    return float(total or 0.0)


def _compute_income_metrics(months: int) -> dict:
    today = date.today()
    current_period_start = _shift_month(_month_start(today), -(months - 1))
    current_period_end = today
    previous_period_end = current_period_start - timedelta(days=1)
    previous_period_start = _shift_month(_month_start(previous_period_end), -(months - 1))

    current_income = _sum_income_between(current_period_start, current_period_end)
    previous_income = _sum_income_between(previous_period_start, previous_period_end)
    change_pct = _compute_pct_change(current_income, previous_income)
    return {
        "current": round(current_income, 2),
        "reference": round(previous_income, 2),
        "change_pct": change_pct,
        "label": f"vs. previous {months} months",
    }


def _category_spending_data(start_date: date, end_date: date) -> dict[int, dict]:
    rows = DBSession.query(
        Transaction.category_id,
        Transaction.amount
    ).join(Category).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Category.type.in_([1, 2]),
        or_(Transaction.saving_id == None, Transaction.saving.has(name="Reste"))
    ).all()

    data = defaultdict(lambda: {"amounts": [], "total": 0.0})
    for category_id, amount in rows:
        value = float(abs(amount or 0))
        entry = data[category_id]
        entry["amounts"].append(value)
        entry["total"] += value
    return data


def _median_value(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(median(values), 2)


def _build_category_stats(months: int) -> dict:
    today = date.today()
    current_start = _shift_month(_month_start(today), -(months - 1))
    current_end = today
    previous_end = current_start - timedelta(days=1)
    previous_start = _shift_month(_month_start(previous_end), -(months - 1))

    current_data = _category_spending_data(current_start, current_end)
    previous_data = _category_spending_data(previous_start, previous_end)

    categories = Category.query.filter(Category.type.in_([1, 2])).all()
    stats = []
    for category in categories:
        current_entry = current_data.get(category.id, {"amounts": [], "total": 0.0})
        previous_entry = previous_data.get(category.id, {"amounts": [], "total": 0.0})

        current_total = current_entry["total"]
        previous_total = previous_entry["total"]
        growth_pct = _compute_pct_change(current_total, previous_total)
        stats.append({
            "category": category,
            "median_spending": _median_value(current_entry["amounts"]),
            "growth_pct": growth_pct
        })

    top_growing = sorted(stats, key=lambda s: s['growth_pct'], reverse=True)[:5]
    top_growing = sorted(stats, key=lambda s: s['growth_pct'], reverse=True)[:5]

    falling_candidates = [s for s in stats if s['median_spending'] > 0]
    top_falling = sorted(falling_candidates, key=lambda s: s['growth_pct'])[:5]

    return {
        "top_growing": top_growing,
        "top_falling": top_falling
    }
