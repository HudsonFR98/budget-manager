from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from sqlalchemy import extract
from budget_manager.models import *

home = Blueprint("home", __name__)

def month_sold():
    """Calculate current month balance"""
    current_month = datetime.today().month
    current_year = datetime.today().year
    total_amount = 0
    transactions = Transaction.query.filter(
        extract('month', Transaction.date) == current_month,
        extract('year', Transaction.date) == current_year,
        ).all()
    for t in transactions:
        total_amount += t.amount
    return total_amount

@home.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    """Main dashboard with financial overview"""
    now = datetime.now()
    total_earnings = sum([category.month_total_amount for category in Category.query.filter(Category.type==0).all()])
    total_budget_fixed_expenses = sum([category.get_month_budget.amount for category in Category.query.filter(Category.type == 1).all() if category.get_month_budget is not None])
    total_fixed_expenses_with_budget = sum([category.month_total_amount for category in Category.query.filter(Category.type == 1).all() if category.get_month_budget is not None])
    total_fixed_expenses = sum([category.month_total_amount for category in Category.query.filter(Category.type == 1).all()])
    total_budget_variable_expenses = sum([category.get_month_budget.amount for category in Category.query.filter(Category.type == 2).all() if category.get_month_budget is not None])
    total_variable_expenses_with_budget = sum([category.month_total_amount for category in Category.query.filter(Category.type == 2).all() if category.get_month_budget is not None])
    total_variable_expenses = sum([category.month_total_amount for category in Category.query.filter(Category.type == 2).all()])
    ctx = {
        "month_sold": month_sold(),
        "current_date": now.strftime("%B %Y"),
        "earnings": Category.query.filter(Category.type==0).all(),
        "total_earnings": total_earnings,
        "fixed_expenses": Category.query.filter(Category.type==1).all(),
        "total_fixed_expenses": total_fixed_expenses,
        "total_conso_fixed_expenses": round(-((total_fixed_expenses_with_budget / (total_budget_fixed_expenses*total_earnings)) * 100), 1) if total_fixed_expenses_with_budget else 0,
        "variable_expenses": Category.query.filter(Category.type==2).all(),
        "total_variable_expenses": total_variable_expenses,
        "total_conso_variable_expenses": round(-((total_variable_expenses_with_budget / (total_budget_variable_expenses*total_earnings)) * 100), 1) if total_variable_expenses_with_budget else 0,
    }
    return render_template('home.html', **ctx)

@home.route('/year_summary', methods=['GET', 'POST'])
@login_required
def dashboard_of_year():
    """Year summary dashboard"""
    now = datetime.now()
    ctx = {
        "current_date": now.strftime("%B %Y")
    }
    return render_template('home.html', ctx=ctx)
