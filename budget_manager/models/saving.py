import logging
from sqlalchemy import Column, Integer, String, Numeric
from budget_manager.lib.database import Base, DBSession

log = logging.getLogger(__name__)


class Saving(Base):
    """Saving model for managing savings"""
    __tablename__ = 'saving'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    note = Column(String(255), nullable=True)
    amount = Column(Numeric(precision=8, scale=2), nullable=False)
    icon = Column(String(30), nullable=True)  # a html class or emoji
    color = Column(String(30), nullable=True)  # hexadecimal
    goal = Column(Numeric(precision=8, scale=2), nullable=True)  # goal amount for this saving

    def __init__(self, name=None, note=None, amount=None, icon=None, color=None, goal=None):
        self.name = name
        self.note = note
        self.amount = amount
        self.icon = icon
        self.color = color
        self.goal = goal

    def __repr__(self):
        return f'<Saving {self.id}: {self.name} - {self.amount}>'


# Add query property to model
Saving.query = DBSession.query_property()

