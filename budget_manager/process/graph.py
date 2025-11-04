from datetime import datetime, timedelta
from flask import request
from sqlalchemy import extract
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import io
import base64
import budget_manager.dao as dao


class StackedSpendingChart():

    def __init__(self):
        
        # Get width and height parameters from the request
        self.width = int(request.args.get('width', 1700))
        self.height = int(request.args.get('height', 800))

        # titles
        self.title = 'Empilement des catégories de dépenses'
        self.y_label = 'Mois/Année'
        self.x_label = 'Montant en €'

        # Generate x-axis labels for the last 12 months
        today = datetime.now()
        self.last_12_months = [today - timedelta(days=30*i) for i in range(11, -1, -1)]
        self.categories = dao.get_spending_categories()

        # Use category colors
        self.colors = [category.color for category in self.categories]

        # Read theme from cookie set by client (fallback to light)
        theme = request.cookies.get('theme', 'light')
        self.is_dark = (str(theme).lower() == 'dark')

        # Theme-aware colors (ensure strong contrast in dark mode)
        self.text_color = '#ffffff' if self.is_dark else '#212529'
        self.axis_color = '#ffffff' if self.is_dark else '#6c757d'
        self.grid_alpha = 0.25 if self.is_dark else 0.3

    def generate(self):

        x_labels = [date.strftime("%m/%y") for date in self.last_12_months]

        # Generate spendings data
        x = np.arange(len(x_labels))
        spending_data = []
        for category in self.categories:
            y = []
            for date in self.last_12_months:
                amount = abs(float(category.given_month_total_amount(month=date.month, year=date.year)))
                y.append(amount)
            spending_data.append(y)
        labels = [category.name for category in self.categories]

        # Create figure/axes with transparent background
        fig, ax = plt.subplots(figsize=(self.width / 100, self.height / 100))
        fig.patch.set_alpha(0.0)  # transparent figure
        ax.set_facecolor('none')  # transparent axes

        # Plot stacked areas
        ax.stackplot(x, *spending_data, labels=labels, colors=self.colors)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, color=self.text_color)

        # Generate income data
        income_data = []
        for date in self.last_12_months:
            transactions = dao.get_month_transac(month=date.month, year=date.year, paypal=True)
            y = dao.turnover(transactions)
            income_data.append(y)
        # Add simple line for income data
        line, = ax.plot(x, income_data, color='#50D735', linestyle='-', label='Line Data', linewidth=1.7)
        shadow_effect = [pe.Stroke(linewidth=4, foreground='green'), pe.Normal()]
        line.set_path_effects(shadow_effect)

        # Generate amount (solde) data
        sold_data = []
        for date in self.last_12_months:
            y = dao.past_sold(month=date.month, year=date.year)
            sold_data.append(y)
        line2, = ax.plot(x, sold_data, color='#FF00AE', linestyle='-', label='Line Data', linewidth=1.7)
        shadow_effect2 = [pe.Stroke(linewidth=4, foreground='purple'), pe.Normal()]
        line2.set_path_effects(shadow_effect2)

        # Axes styling for theme
        for spine in ax.spines.values():
            spine.set_color(self.axis_color)
        ax.tick_params(colors=self.text_color)
        ax.yaxis.label.set_color(self.text_color)
        ax.xaxis.label.set_color(self.text_color)

        # Grid and legend styled for theme
        ax.grid(True, color=self.axis_color, alpha=self.grid_alpha, linewidth=0.6)

        legend = ax.legend(labels, loc='center left', bbox_to_anchor=(1, 0.5))
        # Legend background: white in light mode, transparent in dark mode
        if self.is_dark:
            legend.get_frame().set_facecolor((0, 0, 0, 0))
        else:
            legend.get_frame().set_facecolor('#ffffff')
        legend.get_frame().set_edgecolor(self.axis_color)
        for text in legend.get_texts():
            text.set_color(self.text_color)

        # Titles and labels
        ax.set_title(self.title, color=self.text_color)
        ax.set_xlabel(self.y_label, color=self.text_color)
        ax.set_ylabel(self.x_label, color=self.text_color)

        # Save the plot to a temporary buffer with transparency
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', transparent=True, bbox_inches='tight')
        buffer.seek(0)

        plot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Clear the figure to free memory
        plt.close(fig)

        return plot_base64
