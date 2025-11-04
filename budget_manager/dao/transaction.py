from datetime import datetime, date
from sqlalchemy import extract
from sqlalchemy import or_, and_
from budget_manager.models import *
from budget_manager.lib.database import DBSession
from typing import List

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
    sold at that month (everthing before and this month included)
    """
    total_amount = 0
    transactions = Transaction.query.filter(
        Transaction.date <= date(year, month, 27),
        (Transaction.paypal == False) | (Transaction.paypal == None)
    ).order_by(Transaction.id.desc())
    for t in transactions:
        total_amount += t.amount
    return total_amount
