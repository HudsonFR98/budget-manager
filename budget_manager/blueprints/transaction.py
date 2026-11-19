from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import extract
from sqlalchemy.orm import joinedload
from budget_manager.models import *
from budget_manager.lib.const import SYSTEM_SAVING_NAME
from budget_manager.lib.database import DBSession
from budget_manager.dao.transaction import record_spending_transaction, spending_exceeds_envelope

transaction = Blueprint("transaction", __name__)

def sold():
    """Calculate total balance"""
    total_amount = 0
    transactions = Transaction.query.all()
    for t in transactions:
        total_amount += t.amount
    return total_amount

def reajust_fixed_budgets(old_total_earnings):
    """Readjust fixed budgets when earnings change"""
    new_total_earnings = Transaction.get_budget_eligible_earnings()
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
        old_total_earnings = Transaction.get_budget_eligible_earnings(month=month, year=year)
    try:
        diff = new_total_earnings / old_total_earnings
    except:
        diff = 1 #no change
    for bud in fixed_budgets:
        bud.amount = float(bud.amount) / diff
    DBSession.commit()

@transaction.route('/', methods=['GET', 'POST'])
@login_required
def summary():
    """Transaction management dashboard"""
    current_date = datetime.now()
    start_date = current_date - timedelta(days=31)
    end_date = current_date

    #we display transaction from 1 month max
    transactions = (
        Transaction.query.options(
            joinedload(Transaction.category),
            joinedload(Transaction.saving),
        )
        .filter(
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date(),
        )
        .order_by(Transaction.id.desc())
        .all()
    )
    ctx = {'transactions': transactions,
           'sold': sold()}
    return render_template('transaction/transaction.html', **ctx)

@transaction.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    """Delete a transaction"""
    data = request.get_json()
    id = data.get('id')
    old_total_earnings = Transaction.get_budget_eligible_earnings()
    transac = Transaction.query.get(id)
    if not transac:
        return jsonify({'error': 'Transaction not found'}), 404
    
    transac_type = transac.category.type
    transac_amount = float(transac.amount)
    transac_saving_id = transac.saving_id
    
    # Revert transaction's effect on savings before deleting
    if transac_type == 0:
        # Was earning: revert addition to Base or selected saving
        if transac_saving_id:
            # Revert from selected saving
            saving = Saving.query.get(transac_saving_id)
            if saving:
                saving.amount = max(0, float(saving.amount) - transac_amount)
        else:
            # Revert from Base saving
            base_saving = Saving.query.filter(Saving.name == SYSTEM_SAVING_NAME).first()
            if base_saving:
                base_saving.amount = max(0, float(base_saving.amount) - transac_amount)
    else:
        # Was spending: revert subtraction (add back the absolute value)
        if transac_saving_id:
            saving = Saving.query.get(transac_saving_id)
            if saving:
                spending_amount = abs(transac_amount)  # Convert negative to positive
                saving.amount = float(saving.amount) + spending_amount
    
    DBSession.delete(transac)
    DBSession.commit()
    
    # if earning has changed
    if transac_type == 0:
        # we re-adjust all fixed bugdets
        reajust_fixed_budgets(old_total_earnings)

    return jsonify({'message': 'transaction deleted!'})

@transaction.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new transaction"""
    now = datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        old_total_earnings = Transaction.get_budget_eligible_earnings()
        note = request.form['note']
        category_id = request.form['category']
        date = request.form['date']
        amount = float(request.form['amount'])
        saving_id = request.form.get('saving')
        
        # Validate amount based on category type
        category = Category.query.get(category_id)
        if category.type == 0:  # Earnings - must be positive
            if amount < 0:
                flash('Les revenus (catégorie type 0) doivent être positifs.', 'error')
                savings = Saving.query.order_by(Saving.id).all()
                return render_template('transaction/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all(), savings=savings)
        else:  # Spending (type 1 or 2) - must be negative
            if amount > 0:
                flash('Les dépenses (catégories type 1 et 2) doivent être négatives.', 'error')
                savings = Saving.query.order_by(Saving.id).all()
                return render_template('transaction/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all(), savings=savings)
        
        category = Category.query.get(category_id)
        spending_warning = None
        if category.type == 0:
            transac = Transaction(
                note=note,
                category_id=category_id,
                date=date,
                amount=amount,
                saving_id=saving_id if saving_id else None,
            )
            DBSession.add(transac)
            if saving_id:
                saving = Saving.query.get(saving_id)
                if saving:
                    new_amount = float(saving.amount) + amount
                    if saving.goal:
                        saving.amount = min(new_amount, float(saving.goal))
                    else:
                        saving.amount = new_amount
            else:
                base_saving = Saving.query.filter(Saving.name == SYSTEM_SAVING_NAME).first()
                if base_saving:
                    base_saving.amount = float(base_saving.amount) + amount
                else:
                    all_savings = Saving.query.all()
                    if all_savings:
                        all_savings[0].amount = float(all_savings[0].amount) + amount
        else:
            spending_result = record_spending_transaction(note, category_id, date, amount, saving_id)
            spending_warning = spending_result.warning

        DBSession.commit()

        if spending_warning:
            flash(spending_warning, 'warning')
        
        # if earning has changed
        if category.type == 0:
            #we re-adjust all fixed bugdets
            reajust_fixed_budgets(old_total_earnings)

        return redirect(url_for('transaction.summary'))
    
    savings = Saving.query.order_by(Saving.id).all()
    return render_template('transaction/add_transaction.html', now=now, categories=Category.query.order_by(Category.name).all(), savings=savings)

@transaction.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing transaction"""
    transac = Transaction.query.get(id)
    if not transac:
        flash('Transaction not found!', 'error')
        return redirect(url_for('transaction.summary'))
    
    if request.method == 'POST':
        old_total_earnings = Transaction.get_budget_eligible_earnings()
        old_amount = float(transac.amount)
        old_category_type = transac.category.type
        old_saving_id = transac.saving_id
        
        note = request.form['note']
        category_id = request.form['category']
        date = request.form['date']
        new_amount = float(request.form['amount'])
        new_saving_id = request.form.get('saving')
        
        # Validate amount based on category type
        category = Category.query.get(category_id)
        if category.type == 0:  # Earnings - must be positive
            if new_amount < 0:
                flash('Les revenus doivent être positifs.', 'error')
                savings = Saving.query.order_by(Saving.id).all()
                ctx = {
                    "transac": transac,
                    "categories": Category.query.order_by(Category.name).all(),
                    "savings": savings
                }
                return render_template('transaction/edit_transaction.html', **ctx)
        else:  # Spending (type 1 or 2) - must be negative
            if new_amount > 0:
                flash('Les dépenses doivent être négatives.', 'error')
                savings = Saving.query.order_by(Saving.id).all()
                ctx = {
                    "transac": transac,
                    "categories": Category.query.order_by(Category.name).all(),
                    "savings": savings
                }
                return render_template('transaction/edit_transaction.html', **ctx)
        
        # Revert old transaction's effect on savings
        if old_category_type == 0:
            # Was earning: revert addition to Base or selected saving
            if old_saving_id:
                # Revert from selected saving
                saving = Saving.query.get(old_saving_id)
                if saving:
                    saving.amount = max(0, float(saving.amount) - old_amount)
            else:
                # Revert from Base saving
                base_saving = Saving.query.filter(Saving.name == SYSTEM_SAVING_NAME).first()
                if base_saving:
                    base_saving.amount = max(0, float(base_saving.amount) - old_amount)
        else:
            # Was spending: revert subtraction (add back the absolute value)
            if old_saving_id:
                saving = Saving.query.get(old_saving_id)
                if saving:
                    old_spending_amount = abs(old_amount)  # Convert negative to positive
                    saving.amount = float(saving.amount) + old_spending_amount
        
        category = Category.query.get(category_id)
        if category.type != 0 and spending_exceeds_envelope(new_amount, new_saving_id):
            DBSession.delete(transac)
            DBSession.flush()
            spending_result = record_spending_transaction(
                note, category_id, date, new_amount, new_saving_id,
            )
            DBSession.commit()
            if spending_result.warning:
                flash(spending_result.warning, 'warning')
            return redirect(url_for('transaction.summary'))

        # Update transaction
        transac.note = note
        transac.category_id = category_id
        transac.date = date
        transac.amount = new_amount
        transac.saving_id = new_saving_id if new_saving_id else None
        
        # Apply new transaction's effect on savings
        if category.type == 0:
            # Earning: Add amount to Base saving (or selected saving if provided)
            if new_saving_id:
                # Add to selected saving
                saving = Saving.query.get(new_saving_id)
                if saving:
                    new_amount_value = float(saving.amount) + new_amount
                    # Don't exceed goal if set
                    if saving.goal:
                        saving.amount = min(new_amount_value, float(saving.goal))
                    else:
                        saving.amount = new_amount_value
            else:
                # Add to Base saving by default
                base_saving = Saving.query.filter(Saving.name == SYSTEM_SAVING_NAME).first()
                if base_saving:
                    base_saving.amount = float(base_saving.amount) + new_amount
                else:
                    # No Base saving found, add to first saving
                    all_savings = Saving.query.all()
                    if all_savings:
                        all_savings[0].amount = float(all_savings[0].amount) + new_amount
        else:
            # Spending: Subtract amount from selected saving
            # Amount is already negative for spending, so use absolute value
            if new_saving_id:
                saving = Saving.query.get(new_saving_id)
                if saving:
                    new_spending_amount = abs(new_amount)  # Convert negative to positive
                    saving.amount = max(0, float(saving.amount) - new_spending_amount)

        DBSession.commit()

        if category.type == 0:
            reajust_fixed_budgets(old_total_earnings)
        return redirect(url_for('transaction.summary'))
    
    savings = Saving.query.order_by(Saving.id).all()
    ctx = {
        "transac": transac,
        "categories": Category.query.order_by(Category.name).all(),
        "savings": savings
    }
    return render_template('transaction/edit_transaction.html', **ctx)
