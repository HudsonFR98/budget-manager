import pytest

from flask import session, g
from .fixtures.login import app, login, logout


def test_login_fail(app):
    with app.test_client() as client:
        rv = login(client, 'xxxx', 'yyyy')
        assert b'mauvais utilisateur ou mot de passe' in rv.data


def test_login_success(app):
    with app.test_client() as client:
        rv = login(client, 'bioxadmin', 'icsselloum')
        assert session['user_id'] == 1
        assert g.user.id == 1


def test_logout(app):
    with app.test_client() as client:
        rv = login(client, 'bioxadmin', 'icsbob')
        rv = logout(client)
        assert b'veuillez vous signer a nouveau' in rv.data
        assert g.user is None
