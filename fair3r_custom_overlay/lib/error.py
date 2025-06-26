import logging
import traceback

from flask import session, request, g, current_app
from logging.handlers import SMTPHandler


log = logging.getLogger(__name__)


def get_mail_handler(config=None):
    if config is None:
        # Fallback to current_app if config is not provided (for backward compatibility)
        try:
            config = current_app.config
        except RuntimeError:
            # If we're outside application context, return None
            log.warning("Cannot create mail handler: outside application context")
            return None
    
    try:
        mail_handler = SMTPHandler(
            config['MAIL_SERVER'],
            config['ICS'],
            config['EMAIL_DEV'],
            'Erreur fair3r_custom_overlay',
            credentials=(config['MAIL_USER'], config['MAIL_PASSWORD']),
            secure=())
        mail_handler.setLevel(logging.ERROR)
        return mail_handler
    except Exception as e:
        log.error(f"Failed to create mail handler: {e}")
        return None


def get_error_email(e):
    try:
        # Get the traceback as a string
        tb_str = traceback.format_exc()
        if isinstance(tb_str, bytes):
            tb_str = tb_str.decode('utf-8', errors='replace')

        msg = tb_str + '\n\n'
        msg += 'Paramètres:\n'
        for k, v in request.values.items():
            msg += '%s: %s\n' % (k, v)
        msg += '\nSession:\n'
        for k, v in session.items():
            msg += '%s: %s\n' % (k, v)
        if hasattr(g, 'user') and g.user:
            msg += 'user=%s\n' % g.user.last_name
        msg += '\n\nENVIRONEMENT\n\n'
        for key in sorted(request.environ.keys()):
            msg += '%s: %s\n' % (key, request.environ.get(key))

        return msg
    except Exception as ex:
        # If there's an error formatting the error message, return a simple error message
        return f"Error generating error report: {str(ex)}\nOriginal error: {str(e)}"
