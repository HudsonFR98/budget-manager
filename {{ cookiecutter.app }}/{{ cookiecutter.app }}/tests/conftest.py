import pytest

from sqlalchemy import DDL
from ics.db import sa
from . import util


@pytest.fixture(scope="module", autouse=True)
def connect_db():
    logging.basicConfig(level=CONFIG.LOG_LEVEL)
    sa.open(CONFIG.SQLALCHEMY_DATABASE_URI)
    yield
    util.disconnect()


@pytest.fixture
def with_data(data):
    if not isinstance(data, list):
        data = [data]
    util.load(*data)
    yield
    util.unload(*data)
    util.flush()
