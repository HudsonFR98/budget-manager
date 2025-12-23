import json
import logging
from datetime import datetime, date

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from budget_manager.models import *
from budget_manager.lib.database import DBSession
from budget_manager.blueprints.analytics import _category_median_monthly_spending

category = Blueprint("category", __name__)
log = logging.getLogger(__name__)

@category.route('/', methods=['GET', 'POST'])
@login_required
def summary():
    """Category management dashboard"""
    categories = Category.query.order_by(Category.type.desc()).all()
    data = []
    budget_total = 0
    # depenses, gains..
    for cat in categories:
        try:
            data.append({
                "name": cat.name,
                "label": cat.icon,
                "value": round(float(cat.get_month_budget.amount), 2),
                "color": cat.color
            })
            budget_total += cat.get_month_budget.amount
        except:
            pass
    # epargne
    data.append({
        "label": "🔒",
        "value": 1-float(budget_total),
        "color": "#65cd64"
    })
    median_window = 6
    category_medians = _category_median_monthly_spending(median_window, categories)
    ctx = {
        'categories': categories,
           'data': json.dumps(data),
        'budget_total': round(float(budget_total), 2),
        'category_medians': category_medians,
        'median_window': median_window,
    }
    return render_template('category/category.html', **ctx)

@category.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    """Delete a category"""
    data = request.get_json()
    id = data.get('id')
    cat = Category.query.get(id)
    DBSession.delete(cat)
    DBSession.commit()
    return jsonify({'message': 'category deleted!'})

@category.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new category"""
    total_earnings = Transaction.get_budget_eligible_earnings()
    if request.method == 'POST':
        name = request.form['name'] # or request.get_json().get('name') if xhr json
        type = int(request.form['type'])
        color = request.form['color']
        icon = request.form['icon'] if request.form['icon'] else ""
        cat = Category(name=name, type=type, color=color, icon=icon)
        DBSession.add(cat)
        DBSession.commit()
        try:
            if float(request.form['budget']) > 0 and type != 0:
                bud = Budget(date_val=date.today(), amount=float(request.form['budget']) / 100)
                DBSession.add(bud)
                DBSession.commit()
                cat_bud = category_budget.insert().values(category_id=cat.id, budget_id=bud.id)
                DBSession.execute(cat_bud)
        except Exception as e:
            log.error(f"Error adding budget: {e}")
            pass
        DBSession.commit()
        return redirect(url_for('category.summary'))
    ctx = {
        "total_earnings": total_earnings
    }
    return render_template('category/add_category.html', **ctx)

@category.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing category"""
    total_earnings = Transaction.get_budget_eligible_earnings()
    cat = Category.query.get(id)
    bud = cat.get_month_budget
    if request.method == 'POST':
        try:
            if float(request.form['budget']) > 0:
                if not bud:
                    bud = Budget(date_val=date.today(), amount=float(request.form['budget']) / 100)
                    DBSession.add(bud)
                    DBSession.commit()
                    cat_bud = category_budget.insert().values(category_id=int(id), budget_id=bud.id)
                    DBSession.execute(cat_bud)
                    DBSession.commit()
                else:
                    bud.amount = float(request.form['budget']) / 100
            else:
                if not bud:
                    pass
                else:
                    DBSession.delete(bud)
                    DBSession.commit()
        except Exception as e:
            log.error(f"Error updating budget: {e}")
            pass
        cat.name = request.form['name']
        cat.type = request.form['type']
        cat.color = request.form['color']
        cat.icon = request.form['icon'] if request.form['icon'] else ""
        DBSession.commit()
        return redirect(url_for('category.summary'))
    ctx = {'total_earnings': total_earnings}
    return render_template('category/edit_category.html', cat=cat, **ctx)
