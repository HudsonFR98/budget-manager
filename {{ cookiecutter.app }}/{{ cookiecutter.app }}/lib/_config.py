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
            'filename': '/var/log/{{ cookiecutter.app }}/{{ cookiecutter.app }}.log',
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
        '{{ cookiecutter.app }}': {
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
    DOC_DIR = '/opt/{{ cookiecutter.app }}_docs'
    BASE_URI = '/prive'
    WORKLIST_DIR = os.path.join(DOC_DIR, 'geno', 'worklist')


class ProdConfig(Config):

    CONTEXT = 'prod'
    SQLALCHEMY_DATABASE_URI = {{ cookiecutter.db_prod }}


class DevConfig(Config):

    CONTEXT = 'dev'
    SQLALCHEMY_DATABASE_URI = 'postgresql://web:ph2013_x@%s/mci' \
        % os.environ.get('DB_IP', '')


class DemoConfig(Config):

    CONTEXT = 'demo'
    SQLALCHEMY_DATABASE_URI = 'postgresql://web:ph2013_x@serv-ics-recette2/mci'


class TestConfig(Config):

    TESTING = True
    LOG_LEVEL = logging.ERROR
    SQLALCHEMY_DATABASE_URI = 'postgresql://web:ph2013_x@%s/mci_test' \
        % os.environ.get('DB_IP', '')
    SERVER_NAME = 'localhost'


if '{{ cookiecutter.app|upper }}_CONTEXT' not in os.environ:
    raise Exception("La variable d'environnement {{ cookiecutter.app|upper }}_CONTEXT n'est pas renseignée")

if os.environ['{{ cookiecutter.app|upper }}_CONTEXT'] in ('dev', 'test') and 'DB_IP' not in os.environ:
    raise Exception("La variable d'environnement DB_IP n'est pas renseignée")


_ENV = dict(
    test=TestConfig,
    dev=DevConfig,
    demo=DemoConfig,
    prod=ProdConfig
)
CONFIG = _ENV[os.environ['{{ cookiecutter.app|upper }}_CONTEXT']]
