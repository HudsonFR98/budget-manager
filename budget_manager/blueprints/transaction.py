from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import extract
from budget_manager.models import *
from budget_manager.lib.database import DBSession

transaction = Blueprint("transaction", __name__)

def sold():
    """Calculate total balance"""
    total_amount = 0
    transactions = Transaction.query.filter((Transaction.paypal == False) | (Transaction.paypal == None)).all()
    for t in transactions:
        total_amount += t.amount
    return total_amount

def reajust_fixed_budgets(old_total_earnings):
    """Readjust fixed budgets when earnings change"""
    new_total_earnings = sum([category.month_total_amount for category in Category.query.filter(Category.type == 0).all()])
    fixed_categories = Category.query.filter(Category.type == 1).all()
    fixed_budgets = []
    for cat in fixed_categories:
        if cat.get_month_budget is not None:
            fixed_budgets.append(cat.get_month_budget)
    if old_total_earnings != 0 and new_total_earnings != 0: # normal case
        pass
    if old_total_earnings == 0 and new_total_earnings != 0: #when a new month start, and we need to reprocess budgets according to past month earnings
        current_month = datetime.today().month
        current_year = datetime.today().year
        if current_month != 1:
            year = current_year
            month = current_month
        else:
            year = current_year - 1
            month = 12
        old_total_earnings = sum([category.given_month_total_amount(month, year) for category in Category.query.filter(Category.type == 0).all()])
    try:
        diff = new_total_earnings / old_total_earnings
    except:
        diff = 1 #no change
    for bud in fixed_budgets:
        bud.amount = bud.amount / diff
    DBSession.commit()

@transaction.route('/', methods=['GET', 'POST'])
@login_required
def summary():
    """Transaction management dashboard"""
    current_date = datetime.now()
    start_date = current_date - timedelta(days=31)
    end_date = current_date

    #we display transaction from 1 month max
    transactions = Transaction.query.filter(
        Transaction.date >= start_date.date(),
        Transaction.date < end_date.date(),
        (Transaction.paypal == False) | (Transaction.paypal == None)
    ).order_by(Transaction.id.desc()).all()
    ctx = {'transactions': transactions,
           'sold': sold()}
    return render_template('transaction/transaction.html', **ctx)

@transaction.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    """Delete a transaction"""
    data = request.get_json()
    id = data.get('id')
    old_total_earnings = sum([category.month_total_amount for category in Category.query.filter(Category.type == 0).all()])
    transac = Transaction.query.get(id)
    type = transac.category.type
    DBSession.delete(transac)
    DBSession.commit()
    # if earning has changed
    if type == 0:
        # we re-adjust all fixed bugdets
        reajust_fixed_budgets(old_total_earnings)

    return jsonify({'message': 'transaction deleted!'})

@transaction.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new transaction"""
    now = datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        old_total_earnings = sum([category.month_total_amount for category in Category.query.filter(Category.type == 0).all()])
        note = request.form['note']
        category_id = request.form['category']
        date = request.form['date']
        amount = request.form['amount']
        transac = Transaction(note=note, category_id=category_id, date=date, amount=amount)
        DBSession.add(transac)
        DBSession.commit()
        # if earning has changed
        if transac.category.type == 0:
            #we re-adjust all fixed bugdets
            reajust_fixed_budgets(old_total_earnings)

        return redirect(url_for('transaction.summary'))
    return render_template('transaction/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all())

@transaction.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing transaction"""
    ctx = {}
    if request.method == 'POST':
        old_total_earnings = sum([category.month_total_amount for category in Category.query.filter(Category.type == 0).all()])
        transac = Transaction.query.get(id)
        transac.note = request.form['note']
        transac.category_id = request.form['category']
        transac.date = request.form['date']
        transac.amount = request.form['amount']
        DBSession.commit()
        # if earning has changed
        if transac.category.type == 0:
            # we re-adjust all fixed bugdets
            reajust_fixed_budgets(old_total_earnings)
        return redirect(url_for('transaction.summary'))
    ctx.update({"transac" : Transaction.query.get(id)})
    ctx.update({"categories": Category.query.order_by(Category.name).all()})

    return render_template('transaction/edit_transaction.html', **ctx)
