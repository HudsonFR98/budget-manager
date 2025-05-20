from typing import List
from fair3r_custom_overlay import models


def get_active_users() -> List[models.User]:
    return models.User.query.filter_by(active=True).order_by(models.User.last_name).all()


def get_user(pk: int) -> models.User:
    return models.User.query.get(pk)
