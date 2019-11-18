from {{ cookiecutter.app }} import models


def get_active_users():
    return models.User.quey.filter_by(active=1).order_by(models.User.last_name).all()
