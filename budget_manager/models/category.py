import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, Table, ForeignKey, extract, or_
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
# Import Transaction here to avoid circular imports
from .transaction import Transaction
from budget_manager.lib.const import SYSTEM_SAVING_NAME
from budget_manager.lib.database import Base, DBSession

log = logging.getLogger(__name__)



# Category type constants
CATEGORY_TYPES = {None: "", 0: "Revenus", 1: "Dépenses fixes", 2: "Dépenses variables"}
TYPE_CATEGORIES = {v: k for k, v in CATEGORY_TYPES.items()}

# Association table for category-budget many-to-many relationship
category_budget = Table(
    'category_budget',
    Base.metadata,
    Column('category_id', Integer, ForeignKey('category.id'), primary_key=True),
    Column('budget_id', Integer, ForeignKey('budget.id'), primary_key=True)
)


class Category(Base):
    """Category model for managing expense/income categories"""
    __tablename__ = 'category'
    
    id = Column(Integer, primary_key=True)
    budgets = relationship('Budget', secondary=category_budget, backref='categories')
    name = Column(String(80), nullable=False)
    type = Column(Integer, nullable=True)
    color = Column(String(30), nullable=True)  # hexadecimal
    icon = Column(String(30), nullable=True)  # a html class

    def __init__(self, name, type=None, color=None, icon=None):
        self.name = name
        self.type = type
        self.color = color
        self.icon = icon

    def __repr__(self):
        return f'<Category {self.name}>'

    @property
    def get_number_of_budgets(self):
        """Get the number of budgets associated with this category"""
        return len(self.budgets)

    @property
    def get_type_label(self):
        """Get the type label for this category"""
        return CATEGORY_TYPES[self.type]

    @property
    def month_total_amount(self):
        """Get total amount for current month"""
        current_month = datetime.today().month
        current_year = datetime.today().year
        total_amount = 0
        transactions = Transaction.query.filter(
            extract('month', Transaction.date) == current_month,
            extract('year', Transaction.date) == current_year,
            Transaction.category == self,
            or_(Transaction.saving_id == None, Transaction.saving.has(name=SYSTEM_SAVING_NAME))
        ).all()
        for t in transactions:
            total_amount += t.amount
        return total_amount

    def given_month_total_amount(self, month, year):
        """Get total amount for a given month and year"""
        total_amount = 0
        transactions = Transaction.query.filter(
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year,
            Transaction.category == self,
            or_(Transaction.saving_id == None, Transaction.saving.has(name=SYSTEM_SAVING_NAME))
        ).all()
        for t in transactions:
            total_amount += t.amount
        return total_amount

    @property
    def get_month_budget(self):
        """Get the budget for current month"""
        # get current month and year
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        # filter the budget objects in the category that match the current month and year
        # budgets_current_month = [budget for budget in self.budgets if budget.get_datetime_obj.month == current_month and budget.get_datetime_obj.year == current_year]
        last_budget = self.budgets[0] if self.budgets else None
        # retrieve the first budget object from the list (assuming there's only one budget per month)
        budget_current_month = last_budget
        return budget_current_month

    @property
    def consumed_budget(self):
        """Get percentage of consumed allocated budget"""
        earnings_total = Transaction.get_budget_eligible_earnings()
        try:
            month_total = float(self.month_total_amount)
        except (TypeError, ValueError):
            month_total = 0.0
        month_budget = self.get_month_budget
        if self.get_month_budget is not None:
            try:
                denominator = float(month_budget.amount) * float(earnings_total)
                if denominator == 0:
                    return 0
                return round(-((month_total / denominator) * 100), 1)
            except Exception:
                return 0
        else:
            return 0

    @property
    def get_month_budget_in_euro(self):
        """Get budget calculated knowing allocated budget and total earning"""
        earnings_total = Transaction.get_budget_eligible_earnings()
        month_budget = self.get_month_budget if self.get_month_budget is not None else 0
        if not month_budget:
            return 0
        return round(float(month_budget.amount) * float(earnings_total), 1)

    @property
    def is_deletable(self):
        """Check if category is deletable (no transactions and not linked to a business)"""
        transactions = Transaction.query.filter(Transaction.category == self).all()
        if transactions:
            return False
        from budget_manager.dao.business import category_is_linked
        return not category_is_linked(self.id)


# Add query property to model
Category.query = DBSession.query_property()
