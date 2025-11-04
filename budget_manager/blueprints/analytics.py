from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import budget_manager.dao as dao
import budget_manager.process as process
from budget_manager.models import *

analytics = Blueprint("analytics", __name__)

@analytics.route('/', methods=['GET', 'POST'])
@login_required
def summary():
    """Analytics dashboard with spending charts"""
    plot = process.StackedSpendingChart()
    plot = plot.generate()

    # Render the template with the chart path
    return render_template('analytics/summary.html', chart=plot)
