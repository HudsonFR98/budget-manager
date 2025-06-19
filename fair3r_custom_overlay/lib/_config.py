import os
import logging

from logging.config import dictConfig


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/fair3r_custom_overlay/fair3r_custom_overlay.log',
            'mode': 'w+',
            'maxBytes': 5000000,
            'backupCount': 10,
        },
        'console': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'fair3r_custom_overlay': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False
        },
        'sqlalchemy.engine': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False
        },
    }
})


class Config(object):

    REST_USER = 'icsws'
    REST_PASSWORD = 'Yqa6Pdyg'
    EMAIL_DEV = 'vasseur@igbmc.fr'
    SETTINGS = None
    STATIC_URI = '/static'
    MAIL_SERVER = 'serv-hub.igbmc.u-strasbg.fr'
    MAIL_USER = 'devics'
    MAIL_PASSWORD = 'icsdev#67'
    SECRET_KEY = '5#yqsj4de85s6zzjkncwhjciksd'

    # docs paths
    DOC_DIR = '/opt/fair3r_custom_overlay_docs'
    BASE_URI = '/prive'
    WORKLIST_DIR = os.path.join(DOC_DIR, 'geno', 'worklist')


class ProdConfig(Config):

    CONTEXT = 'prod'
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@serv-ics-db2/fco"
    LOG_LEVEL = logging.ERROR


class DevConfig(Config):

    CONTEXT = 'dev'
    DEBUG = True
    TESTING = False
    LOG_LEVEL = logging.DEBUG
    DB_URI = "postgresql://web:ph2013_x@%s/fco" % os.environ.get('DB_IP', '')
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@%s/fco" \
        % os.environ.get('DB_IP', '')
    PRESERVE_CONTEXT_ON_EXCEPTION = False  # Helps with better error reporting


class DemoConfig(Config):

    CONTEXT = 'demo'
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@serv-ics-fco-d-01/fco"
    LOG_LEVEL = logging.ERROR


class TestConfig(Config):

    CONTEXT = 'test'
    TESTING = True
    LOG_LEVEL = logging.ERROR
    DB_URI = "postgresql://web:ph2013_x@db/fco"
    SQLALCHEMY_DATABASE_URI = DB_URI
    SERVER_NAME = 'localhost'


if 'FAIR3R_CUSTOM_OVERLAY_CONTEXT' not in os.environ:
    raise Exception("La variable d'environnement FAIR3R_CUSTOM_OVERLAY_CONTEXT n'est pas renseignée")

if os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT'] in ('dev', 'test') and 'DB_IP' not in os.environ:
    raise Exception("La variable d'environnement DB_IP n'est pas renseignée")


_envs = dict(
    test=TestConfig,
    dev=DevConfig,
    demo=DemoConfig,
    prod=ProdConfig
)
config = _envs[os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT']]
