import os

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(app_name)s-%(user)s] [%(levelname)s]: [%(action)s] [%(action_type)s] [%(func_name)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'error': {
            'format': '%(asctime)s [%(app_name)s-%(user)s] [ERROR]: [%(action)s] [%(action_type)s] [%(func_name)s] - [%(line_no)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(asctime)s [%(levelname)s]: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'request': {
            'format': '%(asctime)s [%(app_name)s-%(user)s] [%(levelname)s]: [%(action)s] [%(action_type)s] [%(func_name)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'SmartFarmerFlow.log'),
            'maxBytes': 10485760,
            'backupCount': 10,
            'encoding': 'utf-8'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'error',
            'filename': os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'SmartFarmerFlow_errors.log'),
            'maxBytes': 10485760,
            'backupCount': 10,
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        'app': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'werkzeug': {
            'level': 'WARNING',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}

APP_NAME = 'SmartFarmerFlow'
LOG_MODE = os.environ.get('LOG_MODE', 'combined')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')