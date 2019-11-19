from typing import List
from {{ cookiecutter.app }} import models


def get_active_users() -> List[models.User]:
    return models.User.quey.filter_by(active=1).order_by(models.User.last_name).all()


def get_user(pk: int) -> models.User:
    return models.User.query.get(pk)
