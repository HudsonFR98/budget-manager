import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required

import budget_manager.dao as dao
from budget_manager.models import *
from budget_manager.lib.database import DBSession
from budget_manager.blueprints.transaction import reajust_fixed_budgets, sold

paypal = Blueprint("paypal", __name__)

@paypal.route('/', defaults={'year': datetime.now().year})
@paypal.route('/<year>', methods=['GET', 'POST'])
@login_required
def summary(year):
    """
    summary of my paypal wallet (only the stuff that does NOT go into bank account)
    """
    current_date = datetime.now()
    start_date = current_date - timedelta(days=31)
    end_date = current_date

    #we display transaction from 1 month max
    transactions = Transaction.query.filter(
        Transaction.date >= start_date.date(),
        Transaction.date <= end_date.date(),
        Transaction.paypal == True
    ).order_by(Transaction.id.desc()).all()
    
    ctx = {'transactions': transactions}

    return render_template('paypal/paypal.html', **ctx)

@paypal.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    """Delete a PayPal transaction"""
    data = request.get_json()
    id = data.get('id')
    old_total_earnings = Transaction.get_budget_eligible_earnings()
    transac = Transaction.query.get(id)
    type = transac.category.type
    DBSession.delete(transac)
    DBSession.commit()
    # if earning has changed
    if type == 0:
        # we re-adjust all fixed bugdets
        reajust_fixed_budgets(old_total_earnings)

    return jsonify({'message': 'transaction deleted!'})

@paypal.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new PayPal transaction"""
    now = datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        old_total_earnings = Transaction.get_budget_eligible_earnings()
        note = request.form['note']
        category_id = request.form['category']
        date = request.form['date']
        amount = float(request.form['amount'])

        # Validate amount based on category type (same rules as bank transactions)
        category = Category.query.get(category_id)
        if category.type == 0:  # Earnings - must be positive
            if amount < 0:
                flash('Les revenus (catégorie type 0) doivent être positifs.', 'error')
                return render_template('paypal/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all())
        else:  # Spending (type 1 or 2) - must be negative
            if amount > 0:
                flash('Les dépenses (catégories type 1 et 2) doivent être négatives.', 'error')
                return render_template('paypal/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all())

        transac = Transaction(note=note, category_id=category_id, date=date, amount=amount, paypal=True)
        DBSession.add(transac)
        DBSession.commit()
        # if earning has changed
        if transac.category.type == 0:
            # we re-adjust all fixed bugdets
            reajust_fixed_budgets(old_total_earnings)

        if transac.amount < 0:
            # we add the + version of transac to simulate we have already received this money on bank account
            cat_ventes = Category.query.filter(Category.name == "Ventes Elytras").one()
            reverse_transac = Transaction(
                note="ventes",
                category_id=cat_ventes.id,
                date=date,
                amount=abs(amount),
                paypal=True,
            )
            DBSession.add(reverse_transac)
            DBSession.commit()
            if reverse_transac.category.type == 0:
                # we re-adjust all fixed bugdets
                reajust_fixed_budgets(old_total_earnings)

        return redirect(url_for('paypal.summary'))
    return render_template('paypal/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all())

@paypal.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing PayPal transaction"""
    ctx = {}
    if request.method == 'POST':
        old_total_earnings = Transaction.get_budget_eligible_earnings()
        transac = Transaction.query.get(id)

        note = request.form['note']
        category_id = request.form['category']
        date = request.form['date']
        new_amount = float(request.form['amount'])

        # Validate amount based on category type (same rules as bank transactions)
        category = Category.query.get(category_id)
        if category.type == 0:  # Earnings - must be positive
            if new_amount < 0:
                flash('Les revenus doivent être positifs.', 'error')
                ctx.update({"transac": transac})
                ctx.update({"categories": Category.query.order_by(Category.name).all()})
                return render_template('paypal/edit_transaction.html', **ctx)
        else:  # Spending (type 1 or 2) - must be negative
            if new_amount > 0:
                flash('Les dépenses doivent être négatives.', 'error')
                ctx.update({"transac": transac})
                ctx.update({"categories": Category.query.order_by(Category.name).all()})
                return render_template('paypal/edit_transaction.html', **ctx)

        # Apply changes
        transac.note = note
        transac.category_id = category_id
        transac.date = date
        transac.amount = new_amount
        DBSession.commit()

        # if earning has changed
        if transac.category.type == 0:
            # we re-adjust all fixed bugdets
            reajust_fixed_budgets(old_total_earnings)
        return redirect(url_for('paypal.summary'))
    ctx.update({"transac" : Transaction.query.get(id)})
    ctx.update({"categories": Category.query.order_by(Category.name).all()})

    return render_template('paypal/edit_transaction.html', **ctx)
