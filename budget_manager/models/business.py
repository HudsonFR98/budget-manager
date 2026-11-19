from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship

from budget_manager.lib.database import Base, DBSession

SALES_CATEGORY_PREFIX = "Ventes "
EXPENSE_CATEGORY_PREFIX = "Dépenses "


class Business(Base):
    """A side activity tracked with sales and expense categories."""
    __tablename__ = 'business'

    id = Column(Integer, primary_key=True)
    name = Column(String(70), nullable=False, unique=True)
    started_on = Column(Date, nullable=False)
    opening_result = Column(Numeric(precision=8, scale=2), nullable=False, default=0)
    sales_category_id = Column(Integer, ForeignKey('category.id'), nullable=False, unique=True)
    expense_category_id = Column(Integer, ForeignKey('category.id'), nullable=False, unique=True)
    sales_category = relationship('Category', foreign_keys=[sales_category_id])
    expense_category = relationship('Category', foreign_keys=[expense_category_id])

    def __init__(self, name, started_on, opening_result=0, sales_category_id=None, expense_category_id=None):
        self.name = name
        self.started_on = started_on
        self.opening_result = opening_result
        self.sales_category_id = sales_category_id
        self.expense_category_id = expense_category_id

    @staticmethod
    def sales_category_name(business_name: str) -> str:
        return f"{SALES_CATEGORY_PREFIX}{business_name}"

    @staticmethod
    def expense_category_name(business_name: str) -> str:
        return f"{EXPENSE_CATEGORY_PREFIX}{business_name}"

    @property
    def category_names(self) -> list[str]:
        names = []
        if self.sales_category:
            names.append(self.sales_category.name)
        if self.expense_category:
            names.append(self.expense_category.name)
        return names

    def __repr__(self):
        return f'<Business {self.id}: {self.name}>'


Business.query = DBSession.query_property()
