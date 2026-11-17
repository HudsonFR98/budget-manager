from datetime import datetime, date
from calendar import monthrange
from sqlalchemy import extract
from sqlalchemy import or_, and_
from budget_manager.models import *
from budget_manager.lib.database import DBSession
from typing import List, Optional

DEMO_SALARY_NOTE = "Salaire"
DEMO_SALARY_CATEGORY = "Salaire"

TRIM_MONTHS = {1: [1,2,3], 2: [4,5,6], 3:[7,8,9], 4:[10,11,12]}

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
