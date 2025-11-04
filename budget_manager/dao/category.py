from datetime import datetime
from sqlalchemy import extract
from sqlalchemy import or_, and_
from budget_manager.models import *
from budget_manager.lib.database import DBSession
from typing import List

def get_spending_categories() -> List[Category]:
    """ get all categories of spending/expenses type """

    q = Category.query.filter(
        Category.type.in_([TYPE_CATEGORIES["Dépenses fixes"], TYPE_CATEGORIES["Dépenses variables"]])
        )
    return q.all()
