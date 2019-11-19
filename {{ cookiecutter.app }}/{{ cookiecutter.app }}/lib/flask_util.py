import logging

from functools import wraps
from flask import session, url_for, redirect, g

from {{ cookiecutter.app }} import dao
from ics.db import sa

log = logging.getLogger(__name__)


def login_required(func):
    """ decorator to require logged-in user """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return decorated_view


def before_request():
    """ launched before each request """

    g.user = None
    if 'user_id' in session:
        g.user = dao.get_user(session['user_id'])
        g.user.reload_permissions()


def after_request():
    """ launched after each request """

    sa.DBSession.remove()
