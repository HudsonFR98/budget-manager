from dataclasses import dataclass
from datetime import datetime, date
from calendar import monthrange
from typing import List, Optional

from flask_babel import gettext as _
from sqlalchemy import extract
from sqlalchemy import or_, and_

from budget_manager.lib.const import SYSTEM_SAVING_NAME
from budget_manager.lib.database import DBSession
from budget_manager.models import Category, Saving, Transaction

DEMO_SALARY_NOTE = "Salaire"
DEMO_SALARY_CATEGORY = "Salaire"

TRIM_MONTHS = {1: [1,2,3], 2: [4,5,6], 3:[7,8,9], 4:[10,11,12]}


@dataclass
class RecordSpendingResult:
    transactions: List[Transaction]
    warning: Optional[str] = None


def get_base_saving() -> Optional[Saving]:
    return Saving.query.filter(Saving.name == SYSTEM_SAVING_NAME).first()


def _base_saving_pk(base_saving: Optional[Saving]) -> Optional[int]:
    return base_saving.id if base_saving else None


def spending_exceeds_envelope(amount: float, saving_id: str | int | None) -> bool:
    """True when a non-Base saving cannot cover this spending amount."""
    if not saving_id:
        return False
    saving = Saving.query.get(int(saving_id))
    if saving is None or saving.name == SYSTEM_SAVING_NAME:
        return False
    return abs(float(amount)) > float(saving.amount or 0)


def record_spending_transaction(
    note: str,
    category_id: int,
    transac_date,
    amount: float,
    saving_id: str | int | None,
) -> RecordSpendingResult:
    """
    Record a spending transaction and update savings.
    Splits into two rows when a non-Base saving cannot cover the full amount.
    """
    spending_amount = abs(float(amount))
    saving = Saving.query.get(int(saving_id)) if saving_id else None
    base_saving = get_base_saving()
    base_pk = _base_saving_pk(base_saving)

    if saving is None or saving.name == SYSTEM_SAVING_NAME:
        target = saving or base_saving
        transac = Transaction(
            note=note,
            category_id=int(category_id),
            date=transac_date,
            amount=float(amount),
            saving_id=saving.id if saving else base_pk,
        )
        DBSession.add(transac)
        if target:
            target.amount = max(0.0, float(target.amount or 0) - spending_amount)
        return RecordSpendingResult([transac])

    envelope_balance = float(saving.amount or 0)
    if spending_amount <= envelope_balance:
        transac = Transaction(
            note=note,
            category_id=int(category_id),
            date=transac_date,
            amount=float(amount),
            saving_id=saving.id,
        )
        DBSession.add(transac)
        saving.amount = envelope_balance - spending_amount
        return RecordSpendingResult([transac])

    if envelope_balance <= 0:
        transac = Transaction(
            note=note,
            category_id=int(category_id),
            date=transac_date,
            amount=float(amount),
            saving_id=base_pk,
        )
        DBSession.add(transac)
        if base_saving:
            base_saving.amount = max(0.0, float(base_saving.amount or 0) - spending_amount)
        warning = _(
            'La dépense (%(total).2f€) dépasse le solde de « %(name)s » (0,00€). '
            'Le montant intégral a été imputé sur Base.'
        ) % {'total': spending_amount, 'name': saving.name}
        return RecordSpendingResult([transac], warning)

    from_envelope = envelope_balance
    from_base = spending_amount - from_envelope
    envelope_transac = Transaction(
        note=note,
        category_id=int(category_id),
        date=transac_date,
        amount=-from_envelope,
        saving_id=saving.id,
    )
    base_transac = Transaction(
        note=note,
        category_id=int(category_id),
        date=transac_date,
        amount=-from_base,
        saving_id=base_pk,
    )
    DBSession.add_all([envelope_transac, base_transac])
    saving.amount = 0.0
    if base_saving:
        base_saving.amount = max(0.0, float(base_saving.amount or 0) - from_base)

    warning = _(
        'La dépense (%(total).2f€) dépasse le solde de « %(name)s » (%(avail).2f€). '
        '%(avail).2f€ ont été imputés sur cette épargne et %(base).2f€ sur Base.'
    ) % {
        'total': spending_amount,
        'name': saving.name,
        'avail': from_envelope,
        'base': from_base,
    }
    return RecordSpendingResult([envelope_transac, base_transac], warning)

def get_trimester_transac(trim, year, cat_names, paypal=False) -> List[Transaction]:
    """ extract all transactions from specific trimester, year and categories """

    q = Transaction.query.join(Transaction.category).filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date).in_(TRIM_MONTHS[trim]),
        Category.name.in_(cat_names)
    ).order_by(Transaction.id.desc())

    if not paypal:
        q = q.filter((Transaction.paypal == False) | (Transaction.paypal == None))

    return q.all()

def get_year_transac(year, cat_names, paypal=False) -> List[Transaction]:
    """ extract all transactions from specific trimester, year and categories """

    q = Transaction.query.join(Transaction.category).filter(
        extract('year', Transaction.date) == year,
        Category.name.in_(cat_names)
    ).order_by(Transaction.id.desc())

    if not paypal:
        q = q.filter((Transaction.paypal == False) | (Transaction.paypal == None))

    return q.all()

def has_salary_transaction(year: int, month: int) -> bool:
    """True when the demo salary row for this month already exists."""
    return (
        Transaction.query.join(Transaction.category)
        .filter(
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
            Transaction.note == DEMO_SALARY_NOTE,
            Category.name == DEMO_SALARY_CATEGORY,
        )
        .first()
        is not None
    )


def latest_salary_transaction_date() -> Optional[date]:
    """Most recent demo salary transaction date, if any."""
    row = (
        Transaction.query.join(Transaction.category)
        .filter(
            Transaction.note == DEMO_SALARY_NOTE,
            Category.name == DEMO_SALARY_CATEGORY,
        )
        .order_by(Transaction.date.desc())
        .first()
    )
    return row.date if row else None


def get_month_transac(month, year, cat_names=None, paypal=False) -> List[Transaction]:
    """ extract all transactions from specific month, year and categories """

    if cat_names:
        q = Transaction.query.join(Transaction.category).filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month,
            Category.name.in_(cat_names)
        ).order_by(Transaction.id.desc())
    else:
        q = Transaction.query.join(Transaction.category).filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).order_by(Transaction.id.desc())

    if not paypal:
        q = q.filter((Transaction.paypal == False) | (Transaction.paypal == None))

    return q.all()

def turnover(transactions:List[Transaction]) -> float:
    """ total of earnings (spendings are ignored) """

    total = 0
    for t in transactions:
        if t.amount > 0:
            total += t.amount
    return total

def spending(transactions:List[Transaction]) -> float:
    """ total of spendings (earnings are ignored) """

    total = 0
    for t in transactions:
        if t.amount < 0:
            total += t.amount
    return total

def total_income(cat_names):
    """ total income of all possible trimesters (profitability) """

    transactions = Transaction.query.join(Transaction.category).filter(
        Category.name.in_(cat_names)
    ).order_by(Transaction.id.desc())

    total_turnover = turnover(transactions)
    total_spending = spending(transactions)

    return float(total_turnover + total_spending)

def get_all_transactions() -> List[Transaction]:
    """ get all transactions of all years possible """

    q = Transaction.query.all()
    return q

def past_sold(month, year):
    """
    sold at that month (everything before and this month included)
    """
    # Get the last day of the month (handles leap years and months with different lengths)
    last_day = monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    total_amount = 0
    transactions = Transaction.query.filter(
        Transaction.date <= end_date,
        (Transaction.paypal == False) | (Transaction.paypal == None)
    ).order_by(Transaction.id.desc())
    for t in transactions:
        total_amount += t.amount
    return total_amount
