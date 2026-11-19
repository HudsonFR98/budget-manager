from datetime import datetime, date

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from flask_babel import gettext as _

from budget_manager.dao.business import (
    list_businesses,
    get_business,
    create_business,
    update_business,
    delete_business,
)
from budget_manager.lib.business_report import BusinessReport
from budget_manager.lib.exc import DomainError

business = Blueprint("business", __name__)


def _parse_started_on(raw: str) -> date:
    return datetime.strptime(raw, '%Y-%m-%d').date()


def _parse_opening_result(raw: str) -> float:
    return float(raw or 0)


@business.route('/', methods=['GET'])
@login_required
def summary():
    """List businesses with lifetime profitability."""
    businesses = list_businesses()
    rows = []
    for item in businesses:
        report = BusinessReport(item)
        rows.append({
            'business': item,
            'profitability': report.profitability(),
        })
    return render_template('business/list.html', rows=rows)


@business.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a business and its sales and expense categories."""
    if request.method == 'POST':
        try:
            created = create_business(
                request.form.get('name', ''),
                _parse_started_on(request.form['started_on']),
                _parse_opening_result(request.form.get('opening_result', '0')),
            )
        except (ValueError, KeyError):
            flash(_('Please provide a valid start date and opening result.'), 'error')
            return render_template('business/add.html')
        except DomainError as exc:
            flash(str(exc), 'error')
            return render_template('business/add.html')
        flash(_('Business added.'), 'success')
        return redirect(url_for('business.report', id=created.id))
    return render_template('business/add.html')


@business.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit a business name, start date, and opening result."""
    item = get_business(id)
    if item is None:
        flash(_('Business not found.'), 'error')
        return redirect(url_for('business.summary'))
    if request.method == 'POST':
        try:
            update_business(
                item,
                request.form.get('name', ''),
                _parse_started_on(request.form['started_on']),
                _parse_opening_result(request.form.get('opening_result', '0')),
            )
        except (ValueError, KeyError):
            flash(_('Please provide a valid start date and opening result.'), 'error')
            return render_template('business/edit.html', business=item)
        except DomainError as exc:
            flash(str(exc), 'error')
            return render_template('business/edit.html', business=item)
        flash(_('Business updated.'), 'success')
        return redirect(url_for('business.report', id=item.id))
    return render_template('business/edit.html', business=item)


@business.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a business that has no transactions."""
    data = request.get_json() or {}
    item = get_business(data.get('id'))
    if item is None:
        return jsonify({'error': _('Business not found.')}), 404
    try:
        delete_business(item)
    except DomainError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'message': _('Business deleted.')})


@business.route('/<int:id>', defaults={'year': None})
@business.route('/<int:id>/', defaults={'year': None})
@business.route('/<int:id>/<int:year>')
@login_required
def report(id, year):
    """Quarterly turnover, expenses, profit, lifetime result, and chart."""
    item = get_business(id)
    if item is None:
        flash(_('Business not found.'), 'error')
        return redirect(url_for('business.summary'))
    report = BusinessReport(item, year)
    return render_template('business/report.html', **report.template_context())
