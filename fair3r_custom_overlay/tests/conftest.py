import pytest
import logging
from fair3r_custom_overlay.lib import database
from . import util
from fair3r_custom_overlay.lib import config
from fair3r_custom_overlay import create_app


@pytest.fixture(scope="module", autouse=True)
def connect_db():
    logging.basicConfig(level=config.LOG_LEVEL)
    database.open(config.SQLALCHEMY_DATABASE_URI)
    yield
    util.disconnect()


@pytest.fixture
def with_data(data):
    if not isinstance(data, list):
        data = [data]
    util.load(*data)
    yield
    util.unload(*data)
    # util.flush()


@pytest.fixture(scope='module')
def app():
    yield create_app()
