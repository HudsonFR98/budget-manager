import logging
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Numeric, Date
from sqlalchemy.ext.declarative import declared_attr

from budget_manager.lib.database import Base, DBSession

log = logging.getLogger(__name__)


class Budget(Base):
    """Budget model for managing budget allocations"""
    __tablename__ = 'budget'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=date.today, nullable=False)
    amount = Column(Numeric(precision=12, scale=6), nullable=False)  # a float between 0 and 1 (-> percentage)

    def __init__(self, date_val=None, amount=None):
        self.date = date_val if date_val is not None else date.today()
        self.amount = amount

    @property
    def get_datetime(self):
        """Get formatted date string"""
        return self.date.strftime('%d/%m/%Y')

    @property
    def get_datetime_obj(self):
        """Get datetime object"""
        return datetime.combine(self.date, datetime.min.time())

    def __repr__(self):
        return f'<Budget {self.id}: {self.amount} on {self.date}>'


# Add query property to model
Budget.query = DBSession.query_property()
