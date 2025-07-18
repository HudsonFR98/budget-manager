import pytest
from flask import session, g
from ics_standalone_app_template.tests.util import login as login_util, logout as logout_util
from ics_standalone_app_template import create_app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def login():
    """Login helper function."""
    return login_util


@pytest.fixture
def logout():
    """Logout helper function."""
    return logout_util 