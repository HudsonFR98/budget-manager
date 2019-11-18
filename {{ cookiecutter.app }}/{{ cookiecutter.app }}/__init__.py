
from flask import Flask

from .lib import error
from .lib.config import CONFIG
from .lib import flask_util
from .lib import ui
from ics.db import sa

from .blueprints.auth import auth
from .blueprints.admin import admin
from .blueprints.requests import requests
from .blueprints.batch import batch
from .blueprints.rest import rest


def create_app():

    app = Flask(__name__)
    app.config.from_object(CONFIG)
    sa.open(CONFIG.SQLALCHEMY_DATABASE_URI)

    if CONFIG.CONTEXT == 'prod':
        app.logger.addHandler(error.get_mail_handler())

        @app.errorhandler(Exception)
        def unhandled_exception(e):
            app.logger.error(error.get_error_email(e))
            return 'error', 500

    @app.before_request
    def before_request():
        return flask_util.before_request()

    @app.before_request
    def after_request():
        return flask_util.after_request()

    @app.context_processor
    def inject_ui():
        return dict(CONTEXT=CONFIG.CONTEXT)

    app.register_blueprint(auth)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(requests, url_prefix='/requests')
    app.register_blueprint(batch, url_prefix='/batch')
    app.register_blueprint(rest, url_prefix='/rest')

    return app
