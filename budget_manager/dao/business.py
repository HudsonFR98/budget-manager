from datetime import date

from flask_babel import gettext as _
from sqlalchemy.orm import joinedload

from budget_manager.lib.database import DBSession
from budget_manager.lib.demo_month import DEMO_BUSINESS_NAME, DEMO_BUSINESS_STARTED_ON
from budget_manager.lib.exc import DomainError
from budget_manager.models import Business, Category, Transaction

SALES_CATEGORY_COLOR = "#b0ea70"
SALES_CATEGORY_ICON = "🏪"
EXPENSE_CATEGORY_COLOR = "#dfff2a"
EXPENSE_CATEGORY_ICON = "📦"


def _with_categories():
    return Business.query.options(
        joinedload(Business.sales_category),
        joinedload(Business.expense_category),
    )


def list_businesses() -> list[Business]:
    return _with_categories().order_by(Business.name).all()


def get_business(business_id: int) -> Business | None:
    return _with_categories().filter(Business.id == business_id).first()


def get_first_business() -> Business | None:
    return _with_categories().order_by(Business.id.asc()).first()


def create_business(name: str, started_on: date, opening_result: float = 0) -> Business:
    """Create a business and its sales and expense categories."""
    name = (name or "").strip()
    if not name:
        raise DomainError(_("A business name is required."))
    if len(name) > 70:
        raise DomainError(_("A business name cannot exceed 70 characters."))
    if Business.query.filter(Business.name == name).first():
        raise DomainError(_("A business with this name already exists."))

    sales_name = Business.sales_category_name(name)
    expense_name = Business.expense_category_name(name)
    existing = Category.query.filter(Category.name.in_([sales_name, expense_name])).first()
    if existing:
        raise DomainError(_("Categories for this business name already exist."))

    sales = Category(name=sales_name, type=0, color=SALES_CATEGORY_COLOR, icon=SALES_CATEGORY_ICON)
    expenses = Category(name=expense_name, type=2, color=EXPENSE_CATEGORY_COLOR, icon=EXPENSE_CATEGORY_ICON)
    DBSession.add_all([sales, expenses])
    DBSession.flush()

    business = Business(
        name=name,
        started_on=started_on,
        opening_result=opening_result,
        sales_category_id=sales.id,
        expense_category_id=expenses.id,
    )
    DBSession.add(business)
    DBSession.commit()
    return business


def update_business(business: Business, name: str, started_on: date, opening_result: float) -> Business:
    """Update a business and rename its categories when the name changes."""
    name = (name or "").strip()
    if not name:
        raise DomainError(_("A business name is required."))
    if len(name) > 70:
        raise DomainError(_("A business name cannot exceed 70 characters."))

    if name != business.name:
        clash = Business.query.filter(Business.name == name, Business.id != business.id).first()
        if clash:
            raise DomainError(_("A business with this name already exists."))
        sales_name = Business.sales_category_name(name)
        expense_name = Business.expense_category_name(name)
        existing = Category.query.filter(
            Category.name.in_([sales_name, expense_name]),
            Category.id.notin_([business.sales_category_id, business.expense_category_id]),
        ).first()
        if existing:
            raise DomainError(_("Categories for this business name already exist."))
        business.sales_category.name = sales_name
        business.expense_category.name = expense_name
        business.name = name

    business.started_on = started_on
    business.opening_result = opening_result
    DBSession.commit()
    return business


def delete_business(business: Business) -> None:
    """Delete a business and its categories when they have no transactions."""
    has_transactions = Transaction.query.filter(
        Transaction.category_id.in_([business.sales_category_id, business.expense_category_id])
    ).first()
    if has_transactions:
        raise DomainError(_("This business still has transactions and cannot be deleted."))

    sales = business.sales_category
    expenses = business.expense_category
    DBSession.delete(business)
    DBSession.flush()
    if sales:
        DBSession.delete(sales)
    if expenses:
        DBSession.delete(expenses)
    DBSession.commit()


def ensure_demo_business(started_on: date | None = None) -> Business:
    """Return the first business, creating a demo one when the table is empty."""
    existing = get_first_business()
    if existing:
        return existing
    return create_business(
        DEMO_BUSINESS_NAME,
        started_on or DEMO_BUSINESS_STARTED_ON,
        0,
    )


def category_is_linked(category_id: int) -> bool:
    return (
        Business.query.filter(
            (Business.sales_category_id == category_id) | (Business.expense_category_id == category_id)
        ).first()
        is not None
    )
