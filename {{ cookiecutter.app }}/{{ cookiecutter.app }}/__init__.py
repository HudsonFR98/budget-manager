
from flask import Flask

from {{ cookiecutter.app }}.lib import error
from {{ cookiecutter.app }}.lib import config
from {{ cookiecutter.app }}.lib import flask_util
from ics.db import sa

from .blueprints.auth import auth
# from .blueprints.rest import rest


def create_app():

    app = Flask(__name__)
    app.config.from_object(config)
    sa.open(config.SQLALCHEMY_DATABASE_URI)

    if config.CONTEXT == 'prod':
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
        return dict(CONTEXT=config.CONTEXT)

    app.register_blueprint(auth)
    # app.register_blueprint(rest, url_prefix='/rest')

    return app
