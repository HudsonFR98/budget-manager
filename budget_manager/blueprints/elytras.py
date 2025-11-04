import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required

import budget_manager.dao as dao
from budget_manager.models import *

elytras = Blueprint("elytras", __name__)

START = -20.33 #profitability since 2022/04 and 2023/04

@elytras.route('/', defaults={'year': datetime.now().year, 'paypal': False})
@elytras.route('/<year>/<paypal>', methods=['GET', 'POST'])
@login_required
def summary(year, paypal):
    """
    summary for all 4 trimesters
    """

    year = int(year)
    cat_names = ["Ventes Elytras", "Dépenses Elytras"]
    ctx = {"year": year}

    # summary table of top left

    header = {"Chiffre d'affaire":[], 'Dépenses brutes':[], 'Benef final':[]}
    current_year_transacs = {}
    for trim in (1,2,3,4):
        transactions = dao.get_trimester_transac(trim, year, cat_names, paypal)
        current_year_transacs[str(trim)] = transactions
        turnover = dao.turnover(transactions)
        spending = dao.spending(transactions)
        header["Chiffre d'affaire"].append(turnover)
        header['Dépenses brutes'].append(spending)
        header['Benef final'].append(turnover + spending)
    transactions = dao.get_year_transac(year, cat_names, paypal)
    turnover = dao.turnover(transactions)
    spending = dao.spending(transactions)
    header["Chiffre d'affaire"].append(turnover)
    header['Dépenses brutes'].append(spending)
    header['Benef final'].append(turnover + spending)

    # data for chart

    spendings = []
    turnovers = []
    for year in range(year-10, year+1):
        for month in range(1, 12+1):
            transactions = dao.get_month_transac(month, year, cat_names, paypal)
            if transactions:
                turnover_dico = {'amount':float(sum([t.amount for t in transactions if t.amount > 0])), 'month':month, 'year':year}
                spending_dico = {'amount': -(float(sum([t.amount for t in transactions if t.amount < 0]))), 'month': month, 'year': year}
                turnovers.append(turnover_dico)
                spendings.append(spending_dico)

    # others data

    ctx['spending_data'] = json.dumps(spendings)
    ctx['turnover_data'] = json.dumps(turnovers)
    ctx['current_year_transactions'] = current_year_transacs
    ctx['header'] = header
    ctx['profitability'] = round(START + dao.total_income(cat_names), 2)

    return render_template('elytras/elytras.html', **ctx)
