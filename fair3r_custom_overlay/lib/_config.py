import os
import logging
import tempfile

from logging.config import dictConfig


def setup_logging():
    """Set up logging configuration with proper error handling."""
    log_dir = '/var/log/fair3r_custom_overlay'
    log_file = os.path.join(log_dir, 'fair3r_custom_overlay.log')
    
    # Ensure log directory exists and is writable
    try:
        os.makedirs(log_dir, exist_ok=True)
        # Test if we can write to the directory
        test_file = os.path.join(log_dir, '.test_write')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        use_file_handler = True
    except (OSError, PermissionError):
        # If we can't write to the log directory, use a temporary file or console only
        use_file_handler = False
        log_file = os.path.join(tempfile.gettempdir(), 'fair3r_custom_overlay.log')
    
    config = {
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'formatter': 'default',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'fair3r_custom_overlay': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False
            },
            'sqlalchemy.engine': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False
            },
        }
    }
    
    # Add file handler only if we can write to the log directory
    if use_file_handler:
        config['handlers']['file'] = {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_file,
            'mode': 'a',
            'maxBytes': 5000000,
            'backupCount': 10,
        }
        config['loggers']['fair3r_custom_overlay']['handlers'].append('file')
        config['loggers']['sqlalchemy.engine']['handlers'].append('file')
    
    try:
        dictConfig(config)
    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        logging.warning(f"Failed to configure logging: {e}")


# Set up logging when module is imported
setup_logging()


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

    # Session configuration
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # docs paths
    DOC_DIR = '/opt/fair3r_custom_overlay_docs'
    BASE_URI = '/prive'
    WORKLIST_DIR = os.path.join(DOC_DIR, 'geno', 'worklist')


class ProdConfig(Config):

    CONTEXT = 'prod'
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@serv-ics-db2/fco"
    LOG_LEVEL = logging.ERROR
    
    # Secure session settings for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class DevConfig(Config):

    CONTEXT = 'dev'
    DEBUG = True
    TESTING = False
    LOG_LEVEL = logging.DEBUG
    DB_URI = "postgresql://web:ph2013_x@%s/fco" % os.environ.get('DB_IP', '')
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@%s/fco" \
        % os.environ.get('DB_IP', '')
    PRESERVE_CONTEXT_ON_EXCEPTION = False  # Helps with better error reporting
    
    # Development session settings for debugging
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = False  # Allow JavaScript access for debugging


class DemoConfig(Config):

    CONTEXT = 'demo'
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@serv-ics-fco-d-01/fco"
    LOG_LEVEL = logging.ERROR


class TestConfig(Config):

    CONTEXT = 'test'
    TESTING = True
    LOG_LEVEL = logging.ERROR
    DB_URI = "postgresql://web:ph2013_x@%s/fco" % os.environ.get('DB_IP', 'db')
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
