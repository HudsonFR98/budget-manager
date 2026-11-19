import logging
from datetime import date
from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
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
    ratio = Column(Numeric(precision=8, scale=2), nullable=True)

    history_entries = relationship(
        'SavingHistory',
        back_populates='saving',
        cascade='all, delete-orphan',
    )

    def __init__(self, name=None, note=None, amount=None, icon=None, color=None, goal=None, ratio=None):
        self.name = name
        self.note = note
        self.amount = amount
        self.icon = icon
        self.color = color
        self.goal = goal
        self.ratio = ratio

    def __repr__(self):
        return f'<Saving {self.id}: {self.name} - {self.amount}>'


# Add query property to model
Saving.query = DBSession.query_property()


class SavingHistory(Base):
    """Historical snapshot of savings amounts"""
    __tablename__ = 'saving_history'

    id = Column(Integer, primary_key=True)
    saving_id = Column(Integer, ForeignKey('saving.id'), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)
    amount = Column(Numeric(precision=8, scale=2), nullable=False)

    saving = relationship('Saving', back_populates='history_entries')

    def __init__(self, saving_id=None, date_snapshot=None, amount=None):
        self.saving_id = saving_id
        self.date = date_snapshot or date.today()
        self.amount = amount

    def __repr__(self):
        return f'<SavingHistory saving={self.saving_id} date={self.date} amount={self.amount}>'


SavingHistory.query = DBSession.query_property()

