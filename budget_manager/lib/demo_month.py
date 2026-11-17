"""Stdlib-only builder for validation demo months.

Imported by the SQL generator without the Flask app, and by ValidationDemoFiller.
Keep SYSTEM_SAVING_NAME in sync with ``lib.const``.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from random import Random

SYSTEM_SAVING_NAME = "Base"
SENTINEL_SAVING = "Vacances"
DEMO_SALARY_CATEGORY = "Salaire"
DEMO_SALARY_NOTE = "Salaire"

CATEGORIES = [
    ("Salaire", 0, "#6cf561", "💶"),
    ("CAF", 0, "#73e495", "🏠"),
    ("Autres revenus", 0, "#92f375", "💰"),
    ("Loyer", 1, "#ff8d00", "🏡"),
    ("Électricité", 1, "#f3dc25", "⚡️"),
    ("Mobile", 1, "#a3efff", "📞"),
    ("Mutuelle", 1, "#ddf66f", "💊"),
    ("Assurance habitation", 1, "#c5644f", "🏚"),
    ("Alimentation", 2, "#ffb41c", "🍗"),
    ("Loisirs", 2, "#ff6ef3", "🎳"),
    ("Transports", 2, "#cccccc", "🚃"),
    ("Cadeaux", 2, "#ff93cc", "🎁"),
    ("Santé", 2, "#00ffc0", "🦠"),
    ("Vacances", 2, "#fff577", "🏖"),
]

SAVINGS = [
    ("Santé", "Optique et imprévus santé", 180.00, "💊", "#9fd9b9", 250.00, 0.10),
    (SENTINEL_SAVING, "Voyages et week-ends", 420.00, "🏝️", "#9df7ff", 800.00, 0.25),
    ("Réparations voiture", "Entretien exceptionnel", 310.00, "🚙", "#529dff", 1500.00, 0.25),
    ("Informatique", "Matériel et outils", 150.00, "💻", "#ff7776", 600.00, 0.20),
]

BASE_RATIO = 0.20
BASE_START_AMOUNT = 520.00
SAVING_GOALS = {name: goal for name, _note, _amount, _icon, _color, goal, _ratio in SAVINGS}
SAVING_RATIOS = {SYSTEM_SAVING_NAME: BASE_RATIO}
SAVING_RATIOS.update({name: ratio for name, *_rest, ratio in SAVINGS})

BUDGETS = [
    ("Loyer", 0.280000),
    ("Électricité", 0.040000),
    ("Mobile", 0.008000),
    ("Mutuelle", 0.017000),
    ("Alimentation", 0.130000),
    ("Loisirs", 0.050000),
    ("Transports", 0.030000),
]

FOOD_NOTES = ["Courses Lidl", "Boulangerie", "Marché", "Super U", "Fromagerie", "Fruits", "Restaurant", "Café"]
LEISURE_NOTES = ["Cinéma", "Livre", "Concert", "Bowling", "Musée"]
TRANSPORT_NOTES = ["Tram", "Bus", "Essence", "Parking"]


def clip_note(note: str) -> str:
    return note[:30]


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


@dataclass(frozen=True)
class DemoTransaction:
    date: date
    note: str
    amount: float
    category_name: str
    saving_name: str | None
    paypal: bool
    kind: str


class DemoMonthBuilder:
    """Build a realistic month of demo transactions."""

    def __init__(self, rng: Random | None = None):
        self.rng = rng or Random()

    def build(
        self,
        year: int,
        month: int,
        last_day: int | None = None,
        is_current: bool = False,
    ) -> list[DemoTransaction]:
        if last_day is None:
            last_day = calendar.monthrange(year, month)[1]
        rows: list[DemoTransaction] = []
        rng = self.rng

        salary = 2180.00 if month != 6 else 2380.00
        rows.append(DemoTransaction(date(year, month, 1), DEMO_SALARY_NOTE, salary, DEMO_SALARY_CATEGORY, None, False, "income"))
        rows.append(DemoTransaction(date(year, month, 5), "CAF", 192.40, "CAF", None, False, "income"))

        if month in (4, 10):
            rows.append(DemoTransaction(date(year, month, 12), "Remboursement", 45.00, "Autres revenus", None, False, "income"))

        rows.append(DemoTransaction(date(year, month, 3), "Loyer", -720.00, "Loyer", None, False, "expense"))
        elec = round(-62.00 - rng.randint(0, 18) - (10 if month in (1, 2, 11, 12) else 0), 2)
        rows.append(DemoTransaction(date(year, month, 8), "EDF", elec, "Électricité", None, False, "expense"))
        rows.append(DemoTransaction(date(year, month, 6), "Forfait mobile", -19.99, "Mobile", None, False, "expense"))
        rows.append(DemoTransaction(date(year, month, 7), "Mutuelle", -42.00, "Mutuelle", None, False, "expense"))
        if month % 3 == 1:
            rows.append(DemoTransaction(date(year, month, 10), "Assurance hab.", -18.50, "Assurance habitation", None, False, "expense"))

        food_count = 8 if not is_current else 5
        for _ in range(food_count):
            day = rng.randint(2, last_day)
            amount = round(-rng.uniform(14, 68), 2)
            rows.append(DemoTransaction(
                date(year, month, day), clip_note(rng.choice(FOOD_NOTES)), amount, "Alimentation", None, False, "expense",
            ))

        leisure_count = rng.randint(2, 3 if not is_current else 2)
        for _ in range(leisure_count):
            day = rng.randint(4, last_day)
            amount = round(-rng.uniform(8, 38), 2)
            rows.append(DemoTransaction(
                date(year, month, day), clip_note(rng.choice(LEISURE_NOTES)), amount, "Loisirs", None, False, "expense",
            ))

        transport_count = 4 if not is_current else 2
        for _ in range(transport_count):
            day = rng.randint(2, last_day)
            amount = round(-rng.choice([1.80, 1.80, 3.60, 12.50, 38.00]), 2)
            rows.append(DemoTransaction(
                date(year, month, day), clip_note(rng.choice(TRANSPORT_NOTES)), amount, "Transports", None, False, "expense",
            ))

        if month in (5, 11):
            gift_day = min(15, last_day)
            rows.append(DemoTransaction(date(year, month, gift_day), "Anniversaire", -35.00, "Cadeaux", None, False, "expense"))

        if month == 7:
            rows.append(DemoTransaction(date(year, month, 18), "Optique", -89.00, "Santé", "Santé", False, "expense"))

        if month == 8:
            rows.append(DemoTransaction(date(year, month, 4), "Camping", -160.00, "Vacances", SENTINEL_SAVING, False, "expense"))

        if month in (6, 9):
            sales = round(rng.uniform(28, 75), 2)
            rows.append(DemoTransaction(date(year, month, 20), "Vente figurine", sales, "Ventes Elytras", None, True, "income"))
            spend = round(-rng.uniform(12, 40), 2)
            rows.append(DemoTransaction(date(year, month, 21), "Resine / colis", spend, "Dépenses Elytras", None, True, "expense"))

        return rows


class DemoSavingsLedger:
    """In-memory saving balances used when rendering the seed SQL."""

    def __init__(self) -> None:
        self.amounts = {SYSTEM_SAVING_NAME: BASE_START_AMOUNT}
        for name, _note, amount, *_rest in SAVINGS:
            self.amounts[name] = float(amount)

    def apply_income(self, amount: float, saving: str | None) -> None:
        target = saving or SYSTEM_SAVING_NAME
        new_amount = self.amounts[target] + amount
        goal = SAVING_GOALS.get(target)
        if goal is not None:
            new_amount = min(new_amount, float(goal))
        self.amounts[target] = round(new_amount, 2)

    def apply_saving_expense(self, amount: float, saving: str) -> None:
        self.amounts[saving] = round(max(0.0, self.amounts[saving] - abs(amount)), 2)

    def leftover_from_rows(self, rows: list[DemoTransaction], year: int, month: int) -> float:
        total = 0.0
        for row in rows:
            if row.date.year == year and row.date.month == month and not row.saving_name:
                total += float(row.amount)
        return round(total, 2)

    def distribute_leftover(self, leftover: float) -> None:
        if leftover <= 0:
            return
        take = min(leftover, self.amounts[SYSTEM_SAVING_NAME])
        if take <= 0:
            return
        self.amounts[SYSTEM_SAVING_NAME] = round(self.amounts[SYSTEM_SAVING_NAME] - take, 2)
        total_ratio = sum(SAVING_RATIOS.values())
        excess = 0.0
        for name, ratio in SAVING_RATIOS.items():
            share = take * (ratio / total_ratio)
            new_amount = self.amounts[name] + share
            goal = SAVING_GOALS.get(name)
            if goal is not None and new_amount > goal:
                excess += new_amount - goal
                self.amounts[name] = float(goal)
            else:
                self.amounts[name] = new_amount
        if excess > 0.01:
            eligible = [
                name for name in SAVING_RATIOS
                if SAVING_GOALS.get(name) is None or self.amounts[name] < SAVING_GOALS[name]
            ]
            eligible_ratio = sum(SAVING_RATIOS[name] for name in eligible)
            if eligible and eligible_ratio > 0:
                for name in eligible:
                    extra = excess * (SAVING_RATIOS[name] / eligible_ratio)
                    new_amount = self.amounts[name] + extra
                    goal = SAVING_GOALS.get(name)
                    if goal is not None:
                        new_amount = min(new_amount, float(goal))
                    self.amounts[name] = new_amount
        for name in self.amounts:
            self.amounts[name] = round(self.amounts[name], 2)
