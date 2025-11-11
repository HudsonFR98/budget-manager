import json
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from budget_manager.models import *
from budget_manager.lib.database import DBSession

saving = Blueprint("saving", __name__)
log = logging.getLogger(__name__)

# Color palette for savings chart
SAVINGS_COLORS = [
    "#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#F44336",
    "#00BCD4", "#FFC107", "#E91E63", "#3F51B5", "#8BC34A",
    "#FF5722", "#009688", "#795548", "#607D8B", "#CDDC39"
]

def sold():
    """Calculate total balance (same as in transaction blueprint)"""
    total_amount = 0
    transactions = Transaction.query.filter((Transaction.paypal == False) | (Transaction.paypal == None)).all()
    for t in transactions:
        total_amount += t.amount
    return total_amount

@saving.route('/', methods=['GET', 'POST'])
@login_required
def summary():
    """Savings management dashboard"""
    savings = Saving.query.order_by(Saving.id.desc()).all()
    total_amount = sum([float(s.amount) for s in savings])
    total_balance = float(sold())
    
    # Calculate percentage for each saving and prepare chart data
    savings_with_percent = []
    chart_data = []
    for idx, s in enumerate(savings):
        saving_amount = float(s.amount)
        percent = (saving_amount / total_balance * 100) if total_balance > 0 else 0
        
        savings_with_percent.append({
            'saving': s,
            'percent': percent
        })
        
        chart_data.append({
            "name": s.name,
            "label": s.icon if s.icon else "💰",
            "value": saving_amount,
            "color": s.color if s.color else SAVINGS_COLORS[idx % len(SAVINGS_COLORS)]
        })
    
    ctx = {
        'savings_with_percent': savings_with_percent,
        'total_amount': total_amount,
        'total_balance': total_balance,
        'chart_data': json.dumps(chart_data)
    }
    return render_template('saving/saving.html', **ctx)

def adjust_savings_amounts():
    """Adjust saving amounts to match total balance (reusable function for scheduled tasks)"""
    total_balance = float(sold())
    all_savings = Saving.query.all()
    total_savings_amount = sum([float(s.amount) for s in all_savings])
    
    # Check if adjustment is needed
    difference = total_balance - total_savings_amount
    
    if abs(difference) < 0.01:  # Already balanced (within 0.01€ tolerance)
        return 'Savings are already balanced!'
    
    # Find "Reste" saving
    reste_saving = None
    for saving in all_savings:
        if saving.name == "Reste":
            reste_saving = saving
            break
    
    # Step 1: Adjust "Reste" saving first if it exists
    if reste_saving:
        reste_saving.amount = float(reste_saving.amount) + difference
        DBSession.commit()
    
    # Step 2: Check if any saving (including Reste) is negative
    # If Reste is negative, proportionally adjust all savings
    if reste_saving and float(reste_saving.amount) < 0:
        # Reste is negative, need to redistribute proportionally
        negative_amount = abs(float(reste_saving.amount))
        reste_saving.amount = 0  # Set Reste to 0
        
        # Get all other savings (excluding Reste)
        other_savings = [s for s in all_savings if s.id != reste_saving.id]
        
        if other_savings:
            # Calculate total amount in other savings
            total_other_amount = sum([float(s.amount) for s in other_savings])
            
            if total_other_amount >= negative_amount:
                # Redistribute proportionally based on current amounts
                for saving in other_savings:
                    saving_amount = float(saving.amount)
                    if total_other_amount > 0:
                        proportion = saving_amount / total_other_amount
                        reduction = proportion * negative_amount
                        new_amount = max(0, saving_amount - reduction)
                        # Don't exceed goal if set
                        if saving.goal:
                            saving.amount = min(new_amount, float(saving.goal))
                        else:
                            saving.amount = new_amount
                    else:
                        saving.amount = 0
            else:
                # Not enough in other savings, set all to 0
                for saving in other_savings:
                    saving.amount = 0
    
    # Step 3: Ensure no saving goes below 0 and redistribute if needed
    all_savings = Saving.query.all()  # Refresh to get updated amounts
    negative_savings = []
    total_negative = 0
    
    for saving in all_savings:
        if float(saving.amount) < 0:
            negative_savings.append(saving)
            total_negative += abs(float(saving.amount))
            saving.amount = 0  # Set to 0
    
    # If we had negative savings, redistribute the negative amount proportionally
    if negative_savings and total_negative > 0:
        positive_savings = [s for s in all_savings if float(s.amount) > 0]
        
        if positive_savings:
            total_positive = sum([float(s.amount) for s in positive_savings])
            
            if total_positive >= total_negative:
                # Redistribute proportionally
                for saving in positive_savings:
                    saving_amount = float(saving.amount)
                    if total_positive > 0:
                        proportion = saving_amount / total_positive
                        reduction = proportion * total_negative
                        new_amount = max(0, saving_amount - reduction)
                        # Don't exceed goal if set
                        if saving.goal:
                            saving.amount = min(new_amount, float(saving.goal))
                        else:
                            saving.amount = new_amount
            else:
                # Not enough positive savings, set all to 0
                for saving in positive_savings:
                    saving.amount = 0
    
    DBSession.commit()
    
    # Recalculate to ensure balance
    all_savings = Saving.query.all()
    final_total = sum([float(s.amount) for s in all_savings])
    final_difference = total_balance - final_total
    
    # Final adjustment: if still not balanced, adjust Reste or first saving
    # But respect goals - don't exceed goal limits
    if abs(final_difference) >= 0.01:
        if reste_saving:
            new_reste_amount = float(reste_saving.amount) + final_difference
            # Reste typically doesn't have a goal, but check anyway
            if reste_saving.goal:
                reste_saving.amount = min(new_reste_amount, float(reste_saving.goal))
            else:
                reste_saving.amount = new_reste_amount
        elif all_savings:
            # No Reste, adjust first saving that hasn't reached its goal
            for saving in all_savings:
                if not saving.goal or float(saving.amount) < float(saving.goal):
                    new_amount = float(saving.amount) + final_difference
                    if saving.goal:
                        saving.amount = min(new_amount, float(saving.goal))
                    else:
                        saving.amount = new_amount
                    break
        DBSession.commit()
        
        # Final check: ensure no saving exceeds its goal
        all_savings = Saving.query.all()
        for saving in all_savings:
            if saving.goal and float(saving.amount) > float(saving.goal):
                saving.amount = saving.goal
        DBSession.commit()
    
    final_total = sum([float(s.amount) for s in Saving.query.all()])
    return f'Savings amounts adjusted successfully! Total balance: {total_balance}€, Total savings: {final_total}€'

@saving.route('/adjust', methods=['POST'])
@login_required
def adjust():
    """Adjust saving amounts to match total balance"""
    try:
        result = adjust_savings_amounts()
        return jsonify({
            'message': result,
            'status': 'success',
            'total_balance': float(sold()),
            'total_savings': sum([float(s.amount) for s in Saving.query.all()])
        })
    except Exception as e:
        log.error(f"Error adjusting savings: {e}")
        return jsonify({
            'message': f'Error adjusting amounts: {str(e)}',
            'status': 'error'
        }), 500

@saving.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a saving"""
    data = request.get_json()
    id = data.get('id')
    saving_item = Saving.query.get(id)
    if saving_item:
        DBSession.delete(saving_item)
        DBSession.commit()
        return jsonify({'message': 'Saving deleted!'})
    return jsonify({'error': 'Saving not found'}), 404

@saving.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new saving"""
    total_balance = float(sold())
    if request.method == 'POST':
        name = request.form['name']
        note = request.form.get('note', '') or None
        # Use amount-euros if provided, otherwise use amount
        amount = request.form.get('amount-euros') or request.form['amount']
        icon = request.form.get('icon', '') or None
        color = request.form.get('color', '') or None
        goal = request.form.get('goal', '') or None
        if goal:
            goal = float(goal)
        saving_item = Saving(name=name, note=note, amount=amount, icon=icon, color=color, goal=goal)
        DBSession.add(saving_item)
        DBSession.commit()
        flash('Saving added successfully!', 'success')
        return redirect(url_for('saving.summary'))
    ctx = {
        'total_balance': total_balance
    }
    return render_template('saving/add_saving.html', **ctx)

@saving.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing saving"""
    total_balance = float(sold())
    saving_item = Saving.query.get(id)
    if not saving_item:
        flash('Saving not found!', 'error')
        return redirect(url_for('saving.summary'))
    
    if request.method == 'POST':
        saving_item.name = request.form['name']
        saving_item.note = request.form.get('note', '') or None
        # Use amount-euros if provided, otherwise use amount
        saving_item.amount = request.form.get('amount-euros') or request.form['amount']
        saving_item.icon = request.form.get('icon', '') or None
        saving_item.color = request.form.get('color', '') or None
        goal = request.form.get('goal', '') or None
        if goal:
            saving_item.goal = float(goal)
        else:
            saving_item.goal = None
        # Ensure amount doesn't exceed goal if goal is set
        if saving_item.goal and float(saving_item.amount) > float(saving_item.goal):
            saving_item.amount = saving_item.goal
        DBSession.commit()
        flash('Saving updated successfully!', 'success')
        return redirect(url_for('saving.summary'))
    
    # Calculate current percentage for the slider
    current_amount = float(saving_item.amount)
    current_percent = (current_amount / total_balance * 100) if total_balance > 0 else 0
    current_percent = min(current_percent, 100.0)  # Cap at 100%
    
    ctx = {
        'saving': saving_item,
        'total_balance': total_balance,
        'current_percent': current_percent
    }
    return render_template('saving/edit_saving.html', **ctx)

