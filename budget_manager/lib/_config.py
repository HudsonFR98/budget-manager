import os
import logging
import tempfile

from logging.config import dictConfig

"""
Configuration module for budget_manager application.

Deployment Architecture:
- DEV: Uses external database specified by DB_IP environment variable
- TEST/DEMO/PROD: Use Docker containers with local PostgreSQL databases
  - Database container name: 'budman_db_{context}' (e.g., 'budman_db_test', 'budman_db_demo', 'budman_db_prod')
  - Database name: 'budman'
  - All environments accessible on port 8081
  - Deploy vs Update operations supported (data preservation during updates)

Environment Variables:
- BUDGET_MANAGER_CONTEXT: Required for all environments (dev, test, demo, prod)
- DB_IP: Required only for dev environment (external database host)

Session Security:
- All environments currently configured for HTTP (SESSION_COOKIE_SECURE = False)
- When HTTPS is enabled, update SESSION_COOKIE_SECURE to True in respective configs
- SESSION_COOKIE_SAMESITE set to 'Lax' for HTTP compatibility
"""


def setup_logging():
    """Set up logging configuration with proper error handling."""
    log_dir = '/var/log/budget_manager'
    log_file = os.path.join(log_dir, 'budget_manager.log')
    
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
        log_file = os.path.join(tempfile.gettempdir(), 'budget_manager.log')
    
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
            'budget_manager': {
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
        config['loggers']['budget_manager']['handlers'].append('file')
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

def require_env(name: str) -> str:
    """
    Return required env var value
    Raises a clear error if missing/empty.
    """
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        raise RuntimeError(f"La variable d'environnement {name} n'est pas renseignée")
    return value


def build_db_uri() -> str:
    """
    Build SQLAlchemy DB URI from environment variables
    Required:
      - DB_IP
      - POSTGRES_USER
      - POSTGRES_PASSWORD
      - BUDMAN_DB_NAME
    """
    host = require_env("DB_IP")
    user = require_env("POSTGRES_USER")
    password = require_env("POSTGRES_PASSWORD")
    db_name = require_env("BUDMAN_DB_NAME")
    return f"postgresql://{user}:{password}@{host}/{db_name}"

class Config(object):
    """
    Base configuration class.
    
    Session configurations are overridden by environment-specific classes:
    - DEV: Relaxed settings for debugging (HTTP, JavaScript access)
    - TEST/DEMO/PROD: Standard security settings (HTTP, no JavaScript access)
    - All environments currently configured for HTTP compatibility
    - When HTTPS is enabled, update SESSION_COOKIE_SECURE to True
    """

    EMAIL_DEV = 'natha.debanne@gmail.com'
    SETTINGS = None
    STATIC_URI = '/static'
    SECRET_KEY = require_env("SECRET_KEY")

    # Telegram notification settings
    TELEGRAM_BOT_TOKEN = require_env("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = require_env("TELEGRAM_CHAT_ID")

    # Initial admin bootstrap user (used only if no users exist yet)
    ADMIN_USER_USERNAME = require_env("ADMIN_USER_USERNAME")
    ADMIN_USER_PASSWORD = require_env("ADMIN_USER_PASSWORD")
    ADMIN_USER_FIRST_NAME = require_env("ADMIN_USER_FIRST_NAME")
    ADMIN_USER_LAST_NAME = require_env("ADMIN_USER_LAST_NAME")
    ADMIN_USER_EMAIL = require_env("ADMIN_USER_EMAIL")

    # Database (same building blocks in all contexts; DB host differs via DB_IP)
    DB_URI = build_db_uri()
    SQLALCHEMY_DATABASE_URI = DB_URI

    # (Legacy) Email settings kept for backward compatibility, no longer used for errors
    ERROR_EMAIL_FROM = ''
    ERROR_EMAIL_TO = EMAIL_DEV
    ERROR_EMAIL_SMTP_SERVER = ''
    ERROR_EMAIL_SMTP_USER = ''
    ERROR_EMAIL_SMTP_PASSWORD = ''
    ERROR_EMAIL_SMTP_PORT = 587  # Standard SMTP port, adjust if needed

    # Session configuration (base settings, overridden by environment classes)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Babel configuration for internationalization
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    LANGUAGES = {
        'en': 'English',
        'fr': 'Français'
    }


class ProdConfig(Config):

    CONTEXT = 'prod'
    LOG_LEVEL = logging.ERROR
    
    # Session settings for production (HTTP environment)
    SESSION_COOKIE_SECURE = False  # Disabled for HTTP
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Changed from 'Strict' to 'Lax' for better compatibility


class DevConfig(Config):

    CONTEXT = 'dev'
    DEBUG = True
    TESTING = False
    LOG_LEVEL = logging.DEBUG
    PRESERVE_CONTEXT_ON_EXCEPTION = False  # Helps with better error reporting
    
    # Enable Flask's debug toolbar
    DEBUG_TB_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = False  # Allow JavaScript access for debugging
    SESSION_COOKIE_SAMESITE = 'Lax'


class DemoConfig(Config):

    CONTEXT = 'demo'
    LOG_LEVEL = logging.ERROR
    
    # Session settings for demo (HTTP environment)
    SESSION_COOKIE_SECURE = False  # Disabled for HTTP
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Changed from 'Strict' to 'Lax' for better compatibility


class TestConfig(Config):

    CONTEXT = 'test'
    TESTING = True
    LOG_LEVEL = logging.ERROR
    SERVER_NAME = 'localhost'
    
    # Session settings for test (HTTP environment)
    SESSION_COOKIE_SECURE = False  # Disabled for HTTP
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Changed from 'Strict' to 'Lax' for better compatibility



require_env("BUDGET_MANAGER_CONTEXT")
require_env("DB_IP")

_envs = dict(
    test=TestConfig,
    dev=DevConfig,
    demo=DemoConfig,
    prod=ProdConfig
)
config = _envs[os.environ['BUDGET_MANAGER_CONTEXT']]
