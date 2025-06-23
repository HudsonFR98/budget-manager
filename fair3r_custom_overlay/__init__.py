from flask import Flask, render_template
from flask_login import LoginManager

from fair3r_custom_overlay.lib import error
from fair3r_custom_overlay.lib import config
from fair3r_custom_overlay.lib import flask_util
from fair3r_custom_overlay.lib import database
from fair3r_custom_overlay.models import User

from .blueprints.auth import auth
from .blueprints.dashboard import dashboard
from .blueprints.doc import doc
from .blueprints.coverage import coverage
from .blueprints.tests import test_output
# from .blueprints.rest import rest


def create_app():

    app = Flask(__name__)
    app.config.from_object(config)
    
    # Session configuration is now handled in the config file
    # The app.config.from_object(config) above loads all the session settings
    
    database.open(config.SQLALCHEMY_DATABASE_URI)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        return User.query.get(int(user_id))

    # Create admin user if no users exist
    User.create_admin_if_not_exists()

    if config.CONTEXT == 'prod':
        app.logger.addHandler(error.get_mail_handler())

    # Register error handlers for common HTTP errors
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html',
                              error_code=404,
                              error_name='Page Not Found',
                              error_description='The requested page could not be found.'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html',
                              error_code=403,
                              error_name='Forbidden',
                              error_description='You do not have permission to access this resource.'), 403

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('error.html',
                              error_code=400,
                              error_name='Bad Request',
                              error_description='The server could not understand the request.'), 400

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        error_details = error.get_error_email(e)
        app.logger.error(error_details)

        if config.CONTEXT == 'prod':
            # In production, don't show traceback to users
            return render_template('error.html', 
                                  error_code=500,
                                  error_name='Internal Server Error',
                                  error_description='An unexpected error occurred. The administrator has been notified.'), 500
        else:
            # In development, show detailed error information
            import traceback
            return render_template('error.html', 
                                  error_code=500,
                                  error_name='Internal Server Error',
                                  error_description=str(e),
                                  traceback=traceback.format_exc()), 500

    @app.before_request
    def before_request():
        return flask_util.before_request()

    @app.after_request
    def after_request(response):
        flask_util.after_request()
        return response

    @app.context_processor
    def inject_ui():
        return dict(CONTEXT=config.CONTEXT)

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(doc, url_prefix='/doc/')
    # Register coverage blueprint only in test context
    if config.CONTEXT == 'test':
        app.register_blueprint(coverage, url_prefix='/coverage/')
        app.register_blueprint(test_output, url_prefix='/tests/')
    # app.register_blueprint(rest, url_prefix='/rest')

    return app
