import os
import logging
import tempfile

from logging.config import dictConfig

"""
Configuration module for fair3r_custom_overlay application.

Deployment Architecture:
- DEV: Uses external database specified by DB_IP environment variable
- TEST/DEMO/PROD: Use Docker containers with local PostgreSQL databases
  - Database container name: 'db'
  - Database name: 'fco'
  - All environments accessible on port 8080
  - Deploy vs Update operations supported (data preservation during updates)

Environment Variables:
- FAIR3R_CUSTOM_OVERLAY_CONTEXT: Required for all environments (dev, test, demo, prod)
- DB_IP: Required only for dev environment (external database host)
"""


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
    """
    Base configuration class.
    
    Session configurations are overridden by environment-specific classes:
    - DEV: Relaxed settings for debugging
    - TEST/DEMO: Standard security settings
    - PROD: Strict security settings
    """

    REST_USER = 'icsws'
    REST_PASSWORD = 'Yqa6Pdyg'
    EMAIL_DEV = 'vasseur@igbmc.fr'
    SETTINGS = None
    STATIC_URI = '/static'
    MAIL_SERVER = 'serv-hub.igbmc.u-strasbg.fr'
    MAIL_USER = 'devics'
    MAIL_PASSWORD = 'icsdev#67'
    SECRET_KEY = '5#yqsj4de85s6zzjkncwhjciksd'

    # Session configuration (base settings, overridden by environment classes)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # docs paths
    DOC_DIR = '/opt/fair3r_custom_overlay_docs'
    BASE_URI = '/prive'
    WORKLIST_DIR = os.path.join(DOC_DIR, 'geno', 'worklist')


class ProdConfig(Config):

    CONTEXT = 'prod'
    DB_URI = "postgresql://web:ph2013_x@db/fco"
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@db/fco"
    LOG_LEVEL = logging.ERROR
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'


class DevConfig(Config):

    CONTEXT = 'dev'
    DEBUG = True
    TESTING = False
    LOG_LEVEL = logging.DEBUG
    DB_URI = "postgresql://web:ph2013_x@%s/fco" % os.environ.get('DB_IP', '')
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@%s/fco" \
        % os.environ.get('DB_IP', '')
    PRESERVE_CONTEXT_ON_EXCEPTION = False  # Helps with better error reporting
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = False  # Allow JavaScript access for debugging
    SESSION_COOKIE_SAMESITE = 'Lax'


class DemoConfig(Config):

    CONTEXT = 'demo'
    DB_URI = "postgresql://web:ph2013_x@db/fco"
    SQLALCHEMY_DATABASE_URI = "postgresql://web:ph2013_x@db/fco"
    LOG_LEVEL = logging.ERROR
    
    SESSION_COOKIE_SECURE = False  # May not have HTTPS in staging
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestConfig(Config):

    CONTEXT = 'test'
    TESTING = True
    LOG_LEVEL = logging.ERROR
    DB_URI = "postgresql://web:ph2013_x@%s/fco" % os.environ.get('DB_IP', 'db')
    SQLALCHEMY_DATABASE_URI = DB_URI
    SERVER_NAME = 'localhost'
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


if 'FAIR3R_CUSTOM_OVERLAY_CONTEXT' not in os.environ:
    raise Exception("La variable d'environnement FAIR3R_CUSTOM_OVERLAY_CONTEXT n'est pas renseignée")

# Updated validation: only dev environment requires DB_IP (external database)
# test, demo, and prod environments use local Docker container databases
if os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT'] == 'dev' and 'DB_IP' not in os.environ:
    raise Exception("La variable d'environnement DB_IP n'est pas renseignée pour l'environnement de développement")


_envs = dict(
    test=TestConfig,
    dev=DevConfig,
    demo=DemoConfig,
    prod=ProdConfig
)
config = _envs[os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT']]
