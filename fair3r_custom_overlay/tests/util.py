import logging

from fair3r_custom_overlay.lib import database
from fair3r_custom_overlay.lib import config
from fair3r_custom_overlay import models
from sqlalchemy import DDL

# Define our own test utility functions
def with_collections(collections):
    """Decorator to load collections for a test function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            load(collections)
            try:
                return func(*args, **kwargs)
            finally:
                unload(collections)
        return wrapper
    return decorator

def load_collections(collections):
    """Load collections into the database"""
    load(collections)

def unload_collections(collections):
    """Unload collections from the database"""
    unload(collections)

# Alias for backward compatibility
load = load_collections
unload = unload_collections

def connect():
    logging.basicConfig(level=config.LOG_LEVEL)
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    database.open(config.SQLALCHEMY_DATABASE_URI)


def disconnect():
    database.DBSession.remove()


def flush():
    database.DBSession.rollback()
    # Only delete data from our models
    models.User.query.delete()
    models.Role.query.delete()
    commit()


def expire():
    database.DBSession.expire_all()


def commit():
    database.DBSession.commit()


def rollback():
    database.DBSession.rollback()


def login(client, username, password):
    return client.post(
        '/login',
        data=dict(USR=username, PWD=password),
        follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)
