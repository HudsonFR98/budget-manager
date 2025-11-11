import logging
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from budget_manager.lib.database import Base, DBSession

log = logging.getLogger(__name__)


class Transaction(Base):
    """Transaction model for managing financial transactions"""
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today, nullable=False)
    note = Column(String(30), nullable=True)
    amount = Column(Numeric(precision=8, scale=2), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    category = relationship('Category', backref='transactions')
    saving_id = Column(Integer, ForeignKey('saving.id'), nullable=True)
    saving = relationship('Saving', backref='transactions')
    paypal = Column(Boolean, default=False)

    def __init__(self, date=None, note=None, amount=None, category_id=None, saving_id=None, paypal=False):
        self.date = date or date.today()
        self.note = note
        self.amount = amount
        self.category_id = category_id
        self.saving_id = saving_id
        self.paypal = paypal

    @property
    def get_datetime(self):
        """Get formatted date string"""
        return self.date.strftime('%Y-%m-%d')

    @property
    def get_date(self):
        """Get formatted date string for display"""
        return self.date.strftime('%d/%m/%Y')

    @property
    def get_datetime_obj(self):
        """Get datetime object"""
        return datetime.combine(self.date, datetime.min.time())

    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount} on {self.date}>'


# Add query property to model
Transaction.query = DBSession.query_property()
