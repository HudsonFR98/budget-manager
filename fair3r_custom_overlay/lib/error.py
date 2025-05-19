import logging
import traceback

from flask import session, request, g, current_app
from logging.handlers import SMTPHandler


log = logging.getLogger(__name__)


def get_mail_handler():
    conf = current_app.config
    mail_handler = SMTPHandler(
        conf['MAIL_SERVER'],
        conf['ICS'],
        conf['EMAIL_DEV'],
        'Erreur fair3r_custom_overlay',
        credentials=(conf['MAIL_USER'], conf['MAIL_PASSWORD']),
        secure=())
    mail_handler.setLevel(logging.ERROR)
    return mail_handler


def get_error_email(e):

    msg = traceback.format_exc().decode('latin-1') + '\n\n'
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

    return msg.encode('latin-1')
