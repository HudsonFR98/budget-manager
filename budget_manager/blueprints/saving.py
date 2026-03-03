import json
import logging
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from budget_manager.models import *
from budget_manager.lib.database import DBSession
from budget_manager.lib.telegram import send_telegram_message

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


def snapshot_savings_state(snapshot_date=None):
    """Persist current savings amounts for historical analysis."""
    if snapshot_date is None:
        snapshot_date = date.today()

    existing_ids = {
        entry.saving_id
        for entry in SavingHistory.query.filter(SavingHistory.date == snapshot_date).all()
    }

    new_entries = []
    for saving in Saving.query.all():
        if saving.id in existing_ids:
            continue
        new_entries.append(
            SavingHistory(
                saving_id=saving.id,
                date_snapshot=snapshot_date,
                amount=saving.amount
            )
        )

    if new_entries:
        DBSession.add_all(new_entries)
        DBSession.commit()
    return len(new_entries)


def _get_previous_month_year(base_date=None):
    from datetime import datetime

    now = base_date or datetime.now()
    if now.month == 1:
        return 12, now.year - 1
    return now.month - 1, now.year


def _sum_positive_ratios(savings):
    return sum(max(float(s.ratio or 0.0), 0.0) for s in savings)


def _redistribute_proportionally(savings, target_sum: float):
    """Scale given savings so that their ratios sum to target_sum, preserving proportions."""
    savings = [s for s in savings if s is not None]
    if not savings:
        return

    if target_sum <= 0:
        for s in savings:
            s.ratio = 0.0
        return

    current_sum = _sum_positive_ratios(savings)
    if current_sum <= 0:
        per = target_sum / len(savings)
        for s in savings:
            s.ratio = per
        return

    scale = target_sum / current_sum
    for s in savings:
        s.ratio = max(0.0, min(1.0, float(s.ratio or 0.0) * scale))


def _normalize_saving_ratios(updated_saving, new_ratio: float):
    """Normalize ratios so their sum stays at 1 following Reste-first adjustments."""
    new_ratio = max(0.0, min(1.0, new_ratio))
    updated_saving.ratio = new_ratio

    all_savings = Saving.query.order_by(Saving.id).all()
    if not all_savings:
        DBSession.commit()
        return

    if len(all_savings) == 1:
        updated_saving.ratio = 1.0 if new_ratio > 0 else 0.0
        DBSession.commit()
        return

    reste_saving = next((s for s in all_savings if s.name == "Reste"), None)

    # If "Reste" is missing, fall back to proportional scaling for others.
    if not reste_saving:
        others = [s for s in all_savings if s.id != updated_saving.id]
        _redistribute_proportionally(others, max(0.0, 1.0 - new_ratio))
        DBSession.commit()
        return

    if updated_saving.id == reste_saving.id:
        # Editing "Reste": redistribute all other ratios proportionally.
        others = [s for s in all_savings if s.id != reste_saving.id]
        _redistribute_proportionally(others, max(0.0, 1.0 - float(reste_saving.ratio or 0.0)))
        DBSession.commit()
        return

    rest_target = max(0.0, 1.0 - new_ratio)
    rest_savings = [s for s in all_savings if s.id != updated_saving.id]
    rest_current_sum = _sum_positive_ratios(rest_savings)

    reste_current = max(float(reste_saving.ratio or 0.0), 0.0)
    delta = rest_target - rest_current_sum
    max_reste_allowed = rest_target
    new_reste_ratio = reste_current + delta
    new_reste_ratio = min(max(new_reste_ratio, 0.0), max_reste_allowed)
    reste_saving.ratio = new_reste_ratio

    remaining_target = max(0.0, rest_target - new_reste_ratio)
    other_savings = [s for s in rest_savings if s.id != reste_saving.id]
    _redistribute_proportionally(other_savings, remaining_target)

    total_sum = _sum_positive_ratios(all_savings)
    diff = 1.0 - total_sum
    if abs(diff) > 1e-6:
        adjust_target = reste_saving if reste_saving.id != updated_saving.id else (other_savings[0] if other_savings else updated_saving)
        if adjust_target:
            adjusted = max(float(adjust_target.ratio or 0.0) + diff, 0.0)
            adjust_target.ratio = min(1.0, adjusted)

    DBSession.commit()

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
        saving_ratio = float(s.ratio) if getattr(s, "ratio", None) is not None else 0.0
        
        savings_with_percent.append({
            'saving': s,
            'percent': percent
        })
        
        chart_data.append({
            "name": s.name,
            "label": s.icon if s.icon else "💰",
            "value": saving_amount,
            "ratio": saving_ratio,
            "color": s.color if s.color else SAVINGS_COLORS[idx % len(SAVINGS_COLORS)]
        })
    
    # Calculate previous month's "Reste pour épargner" for display
    prev_month, prev_year = _get_previous_month_year()
    leftover_for_savings = calculate_leftover_for_savings(prev_month, prev_year)
    
    ctx = {
        'savings_with_percent': savings_with_percent,
        'total_amount': total_amount,
        'total_balance': total_balance,
        'chart_data': json.dumps(chart_data),
        'leftover_for_savings': leftover_for_savings
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

@saving.route('/distribute-monthly', methods=['POST'])
@login_required
def distribute_monthly():
    """Manually trigger monthly savings distribution"""
    try:
        prev_month, prev_year = _get_previous_month_year()
        result = distribute_monthly_savings(month=prev_month, year=prev_year)
        return jsonify({
            'message': result,
            'status': 'success'
        })
    except Exception as e:
        log.error(f"Manual monthly distribution failed: {e}")
        return jsonify({
            'message': f'Error distributing monthly savings: {str(e)}',
            'status': 'error'
        }), 500


@saving.route('/snapshot', methods=['POST'])
@login_required
def snapshot():
    """Manually capture a snapshot of current savings."""
    try:
        created = snapshot_savings_state()
        msg = f'Snapshot stored ({created} entries created).' if created else 'Snapshot already up to date for today.'
        return jsonify({
            'message': msg,
            'status': 'success'
        })
    except Exception as e:
        log.error(f"Manual snapshot failed: {e}")
        return jsonify({
            'message': f'Error capturing snapshot: {str(e)}',
            'status': 'error'
        }), 500

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
        raw_ratio = (request.form.get('ratio') or '').strip()

        if goal:
            goal = float(goal)

        # Parse ratio; default to 0 if empty
        ratio = 0.0
        if raw_ratio:
            try:
                ratio = float(raw_ratio)
            except ValueError:
                flash('Invalid ratio value. Please enter a number between 0 and 1.', 'error')
                ctx = {'total_balance': total_balance}
                return render_template('saving/add_saving.html', **ctx)

        if ratio < 0 or ratio > 1:
            flash('Ratio must be between 0 and 1.', 'error')
            ctx = {'total_balance': total_balance}
            return render_template('saving/add_saving.html', **ctx)

        saving_item = Saving(name=name, note=note, amount=amount, icon=icon, color=color, goal=goal, ratio=ratio)
        DBSession.add(saving_item)
        DBSession.commit()

        # Normalize ratios so that their sum is 1, based on this new saving's ratio
        _normalize_saving_ratios(saving_item, ratio)

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
        raw_ratio = (request.form.get('ratio') or '').strip()

        if goal:
            saving_item.goal = float(goal)
        else:
            saving_item.goal = None

        # Parse ratio; default to current or 0 if empty
        if raw_ratio:
            try:
                new_ratio = float(raw_ratio)
            except ValueError:
                flash('Invalid ratio value. Please enter a number between 0 and 1.', 'error')
                ctx = {
                    'saving': saving_item,
                    'total_balance': total_balance,
                    'current_percent': (float(saving_item.amount) / total_balance * 100) if total_balance > 0 else 0
                }
                return render_template('saving/edit_saving.html', **ctx)

            if new_ratio < 0 or new_ratio > 1:
                flash('Ratio must be between 0 and 1.', 'error')
                ctx = {
                    'saving': saving_item,
                    'total_balance': total_balance,
                    'current_percent': (float(saving_item.amount) / total_balance * 100) if total_balance > 0 else 0
                }
                return render_template('saving/edit_saving.html', **ctx)

            saving_item.ratio = new_ratio
        else:
            # If left empty, treat as 0 (this saving opts out of leftover distribution)
            saving_item.ratio = 0.0

        # Ensure amount doesn't exceed goal if goal is set
        if saving_item.goal and float(saving_item.amount) > float(saving_item.goal):
            saving_item.amount = saving_item.goal
        DBSession.commit()

        # Normalize ratios after updating this saving
        _normalize_saving_ratios(saving_item, float(saving_item.ratio or 0.0))

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

def calculate_leftover_for_savings(month=None, year=None):
    """Calculate leftover amount for savings for a given month
    
    Args:
        month: Month number (1-12). If None, uses current month.
        year: Year. If None, uses current year.
    
    Returns:
        float: The remaining amount for saving after all expenses
    """
    from datetime import datetime
    from sqlalchemy import extract
    
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    # Calculate total earnings for the month
    total_earnings = 0
    earning_categories = Category.query.filter(Category.type == 0).all()
    for category in earning_categories:
        # Get transactions for this category in the specified month
        transactions = Transaction.query.filter(
            Transaction.category_id == category.id,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).all()
        for t in transactions:
            # Only count transactions registered against "Reste" (or no saving)
            if t.saving_id and (not t.saving or t.saving.name != "Reste"):
                continue
            total_earnings += float(t.amount)
    
    # Calculate total fixed expenses for the month
    total_fixed_expenses = 0
    fixed_categories = Category.query.filter(Category.type == 1).all()
    for category in fixed_categories:
        transactions = Transaction.query.filter(
            Transaction.category_id == category.id,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).all()
        for t in transactions:
            # Only count transactions registered against "Reste" (or no saving)
            if t.saving_id and (not t.saving or t.saving.name != "Reste"):
                continue
            total_fixed_expenses += float(t.amount)
    
    # Calculate total variable expenses for the month
    total_variable_expenses = 0
    variable_categories = Category.query.filter(Category.type == 2).all()
    for category in variable_categories:
        transactions = Transaction.query.filter(
            Transaction.category_id == category.id,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).all()
        for t in transactions:
            # Only count transactions registered against "Reste" (or no saving)
            if t.saving_id and (not t.saving or t.saving.name != "Reste"):
                continue
            total_variable_expenses += float(t.amount)
    
    # Leftover for savings = total_earnings + total_fixed_expenses + total_variable_expenses
    # (expenses are negative, so this gives: earnings - |expenses|)
    leftover_for_savings = total_earnings + total_fixed_expenses + total_variable_expenses
    
    return leftover_for_savings

def distribute_monthly_savings(month=None, year=None):
    """Distribute leftover savings among all savings at end of month
    
    This function:
    1. Calculates 'Reste pour épargner' for the specified month
    2. Removes that amount from 'Reste' saving
    3. Distributes it proportionally among all savings (including Reste)
    
    Args:
        month: Month number (1-12). If None, uses previous month.
        year: Year. If None, uses current year (or previous year if month is previous).
    
    Returns:
        str: Result message
    """
    from datetime import datetime
    from calendar import monthrange
    
    # If month/year not provided, use previous month
    now = datetime.now()
    if month is None:
        if now.month == 1:
            month = 12
            year = now.year - 1
        else:
            month = now.month - 1
            year = now.year
    elif year is None:
        year = now.year
    
    # Calculate leftover for savings for the month
    leftover_for_savings = calculate_leftover_for_savings(month, year)
    
    if leftover_for_savings <= 0:
        return f'No remaining amount to distribute for {month}/{year}. Leftover for savings: {leftover_for_savings:.2f}€'
    
    # Find "Reste" saving
    reste_saving = Saving.query.filter(Saving.name == "Reste").first()
    if not reste_saving:
        return f'No "Reste" saving found. Cannot distribute monthly savings.'
    
    # Get current amount in Reste saving
    reste_amount = float(reste_saving.amount)
    
    # We need to take the leftover amount FROM Reste saving
    # But only if Reste has at least that amount
    if reste_amount < leftover_for_savings:
        # Not enough in Reste, use what's available (but warn the user)
        amount_to_distribute = reste_amount
        reste_saving.amount = 0
        log.warning(f'Reste saving ({reste_amount:.2f}€) has less than calculated leftover ({leftover_for_savings:.2f}€). Distributing available amount.')
    else:
        # Take exactly the leftover amount from Reste
        amount_to_distribute = leftover_for_savings
        reste_saving.amount = reste_amount - leftover_for_savings
    
    # Commit the Reste saving update first
    DBSession.commit()
    
    # Get all savings (including Reste) for proportional distribution
    all_savings = Saving.query.all()
    
    if not all_savings:
        return 'No savings found. Cannot distribute monthly savings.'

    # Prefer ratios for distribution; fall back to amount-based if no ratios set
    ratio_savings = [s for s in all_savings if s.ratio is not None and float(s.ratio) > 0]
    total_ratio = sum(float(s.ratio) for s in ratio_savings)

    if total_ratio > 0 and ratio_savings:
        # Ratio-based distribution
        excess_amount = 0.0

        # First pass: distribute by ratio, respecting goals
        for saving in ratio_savings:
            share = amount_to_distribute * (float(saving.ratio) / total_ratio)
            new_amount = float(saving.amount) + share

            if saving.goal:
                if new_amount > float(saving.goal):
                    excess_amount += (new_amount - float(saving.goal))
                    saving.amount = saving.goal
                else:
                    saving.amount = new_amount
            else:
                saving.amount = new_amount

        # Second pass: redistribute any excess among savings still below goal, using their ratios
        if excess_amount > 0.01:
            still_eligible = [
                s for s in ratio_savings
                if not s.goal or float(s.amount) < float(s.goal)
            ]
            total_ratio_eligible = sum(float(s.ratio) for s in still_eligible)

            if still_eligible and total_ratio_eligible > 0:
                for saving in still_eligible:
                    extra_share = excess_amount * (float(saving.ratio) / total_ratio_eligible)
                    new_amount = float(saving.amount) + extra_share
                    if saving.goal:
                        saving.amount = min(new_amount, float(saving.goal))
                    else:
                        saving.amount = new_amount
    else:
        # Legacy behavior: distribute based on current savings amounts
        total_savings_amount = sum([float(s.amount) for s in all_savings])

        if total_savings_amount > 0:
            excess_amount = 0
            for saving in all_savings:
                saving_amount = float(saving.amount)
                percent = (saving_amount / total_savings_amount * 100) if total_savings_amount > 0 else 0
                proportional_amount = (percent / 100) * amount_to_distribute
                new_amount = float(saving.amount) + proportional_amount

                if saving.goal:
                    if new_amount > float(saving.goal):
                        excess_amount += (new_amount - float(saving.goal))
                        saving.amount = saving.goal
                    else:
                        saving.amount = new_amount
                else:
                    saving.amount = new_amount

            if excess_amount > 0.01:
                still_eligible = [s for s in all_savings if not s.goal or float(s.amount) < float(s.goal)]
                if still_eligible:
                    total_still_eligible = sum([float(s.amount) for s in still_eligible])
                    if total_still_eligible > 0:
                        for saving in still_eligible:
                            saving_amount = float(saving.amount)
                            proportion = saving_amount / total_still_eligible
                            additional = proportion * excess_amount
                            new_amount = float(saving.amount) + additional
                            if saving.goal:
                                saving.amount = min(new_amount, float(saving.goal))
                            else:
                                saving.amount = new_amount
                    else:
                        equal_excess = excess_amount / len(still_eligible)
                        for saving in still_eligible:
                            new_amount = float(saving.amount) + equal_excess
                            if saving.goal:
                                saving.amount = min(new_amount, float(saving.goal))
                            else:
                                saving.amount = new_amount
        else:
            # If balance is 0 or negative, distribute equally
            equal_amount = amount_to_distribute / len(all_savings)
            for saving in all_savings:
                new_amount = float(saving.amount) + equal_amount
                if saving.goal:
                    saving.amount = min(new_amount, float(saving.goal))
                else:
                    saving.amount = new_amount
    
    DBSession.commit()
    
    # Send Telegram notification
    try:
        # Get final amounts for each saving to show in notification
        final_savings = Saving.query.all()
        savings_summary = []
        for saving in final_savings:
            savings_summary.append(f"  • {saving.name}: {float(saving.amount):.2f}€")
        
        message = f"💰 *[BUDGET MANAGER] Monthly Savings Distribution*\n\n"
        message += f"📅 Month: {month}/{year}\n"
        message += f"💵 Amount distributed: {amount_to_distribute:.2f}€\n"
        message += f"📤 From: Reste pour épargner\n\n"
        message += f"📊 *Final Savings Amounts:*\n"
        message += "\n".join(savings_summary)
        send_telegram_message(message)
    except Exception as e:
        log.error(f"Failed to send Telegram notification for monthly distribution: {e}")
    
    return f'Distributed {amount_to_distribute:.2f}€ from "Reste pour épargner" ({month}/{year}) among all savings successfully!'

