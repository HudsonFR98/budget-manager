import pytest

from flask import session, g
from .fixtures.login import app, login, logout
from .fixtures.user import DATA


@pytest.mark.parametrize('data', [DATA])
def test_login_fail(with_data, app):
    with app.test_client() as client:
        rv = login(client, 'xxxx', 'yyyy')
        assert b'mauvais utilisateur ou mot de passe' in rv.data


@pytest.mark.parametrize('data', [DATA])
def test_login_success(with_data, app):
    with app.test_client() as client:
        rv = login(client, 'bioxadmin', 'icsselloum')
        assert session['user_id'] == 1
        assert g.user.id == 1


@pytest.mark.parametrize('data', [DATA])
def test_logout(with_data, app):
    with app.test_client() as client:
        rv = login(client, 'bioxadmin', 'icsselloum')
        rv = logout(client)
        assert b'veuillez vous signer a nouveau' in rv.data
        assert g.user is None
