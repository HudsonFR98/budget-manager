from flask_babel import gettext as _

from budget_manager.models import Saving, Transaction
from budget_manager.lib.const import SYSTEM_SAVING_NAME
from budget_manager.lib.database import DBSession
from budget_manager.lib.exc import DomainError


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


def delete_saving(saving: Saving) -> None:
    """Remove a saving, delete its history, and return any remaining balance to Base."""
    if saving.name == SYSTEM_SAVING_NAME:
        raise DomainError(_("The Base saving cannot be deleted."))

    remaining = float(saving.amount or 0)
    if remaining > 0:
        base_saving = lock_saving_by_name(SYSTEM_SAVING_NAME)
        if not base_saving:
            raise DomainError(_('No "{name}" saving found. Cannot delete saving with a balance.').format(
                name=SYSTEM_SAVING_NAME,
            ))
        base_saving.amount = float(base_saving.amount or 0) + remaining

    Transaction.query.filter(Transaction.saving_id == saving.id).update(
        {Transaction.saving_id: None},
        synchronize_session=False,
    )

    DBSession.delete(saving)
    DBSession.commit()
