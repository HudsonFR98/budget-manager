import json
from datetime import datetime

from flask_babel import gettext as _

import budget_manager.dao as dao
from budget_manager.models import Business


class BusinessReport:
    """Yearly profitability report for one business."""

    def __init__(self, business: Business, year: int | None = None):
        self.business = business
        self.year = int(year or datetime.now().year)
        self.cat_names = business.category_names

    def header(self) -> dict:
        turnover_label = _("Turnover")
        expenses_label = _("Gross expenses")
        profit_label = _("Final profit")
        header = {
            turnover_label: [],
            expenses_label: [],
            profit_label: [],
        }
        for trim in (1, 2, 3, 4):
            transactions = dao.get_trimester_transac(trim, self.year, self.cat_names)
            turnover = dao.turnover(transactions)
            spending = dao.spending(transactions)
            header[turnover_label].append(turnover)
            header[expenses_label].append(spending)
            header[profit_label].append(turnover + spending)

        year_transactions = dao.get_year_transac(self.year, self.cat_names)
        turnover = dao.turnover(year_transactions)
        spending = dao.spending(year_transactions)
        header[turnover_label].append(turnover)
        header[expenses_label].append(spending)
        header[profit_label].append(turnover + spending)
        return header

    def trimester_transactions(self) -> dict:
        current_year_transacs = {}
        for trim in (1, 2, 3, 4):
            current_year_transacs[str(trim)] = dao.get_trimester_transac(
                trim, self.year, self.cat_names
            )
        return current_year_transacs

    def chart_series(self) -> tuple[list[dict], list[dict]]:
        """Monthly turnover and spending for the report year only."""
        spendings = []
        turnovers = []
        for month in range(1, 13):
            transactions = dao.get_month_transac(month, self.year, self.cat_names)
            if not transactions:
                continue
            turnovers.append({
                'amount': float(sum(t.amount for t in transactions if t.amount > 0)),
                'month': month,
                'year': self.year,
            })
            spendings.append({
                'amount': -(float(sum(t.amount for t in transactions if t.amount < 0))),
                'month': month,
                'year': self.year,
            })
        return spendings, turnovers

    def profitability(self) -> float:
        opening = float(self.business.opening_result or 0)
        return round(opening + dao.total_income(self.cat_names), 2)

    def previous_year(self) -> int | None:
        start_year = self.business.started_on.year if self.business.started_on else self.year
        candidate = self.year - 1
        if candidate >= start_year:
            return candidate
        return None

    def next_year(self) -> int | None:
        current_year = datetime.now().year
        candidate = self.year + 1
        if candidate <= current_year:
            return candidate
        return None

    def template_context(self) -> dict:
        spendings, turnovers = self.chart_series()
        return {
            'business': self.business,
            'year': self.year,
            'header': self.header(),
            'current_year_transactions': self.trimester_transactions(),
            'profitability': self.profitability(),
            'spending_data': json.dumps(spendings),
            'turnover_data': json.dumps(turnovers),
            'previous_year': self.previous_year(),
            'next_year': self.next_year(),
        }
