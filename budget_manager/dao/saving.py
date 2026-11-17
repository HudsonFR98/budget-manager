from budget_manager.models import Saving
from budget_manager.lib.database import DBSession


def get_saving_by_name(name: str) -> Saving | None:
    """Return a saving by exact name, or None."""
    return Saving.query.filter(Saving.name == name).first()


def lock_saving_by_name(name: str) -> Saving | None:
    """Lock a saving row for the rest of the transaction."""
    return (
        DBSession.query(Saving)
        .filter(Saving.name == name)
        .with_for_update()
        .first()
    )
