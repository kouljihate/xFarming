from app.database import get_db
from datetime import datetime
import logging
import sys

def log_message(level, message, user_id=None, username=None):
    """
    Log a message to MongoDB logs collection.
    Levels: 'info', 'warning', 'error'
    """
    if level not in ['info', 'warning', 'error']:
        level = 'info'
    
    db = get_db()
    log_entry = {
        'level': level,
        'message': message,
        'timestamp': datetime.utcnow(),
        'user_id': user_id,
        'username': username
    }
    db.logs.insert_one(log_entry)

def get_logs(page=1, per_page=50, level=None):
    db = get_db()
    query = {}
    if level:
        query['level'] = level
    
    total = db.logs.count_documents(query)
    skip = (page - 1) * per_page
    logs = list(db.logs.find(query).sort('timestamp', -1).skip(skip).limit(per_page))
    
    for log in logs:
        log['_id'] = str(log['_id'])
    
    return logs, total

class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + '%(levelname)s: %(message)s' + reset,
        logging.INFO: '\x1b[32m' + '%(levelname)s: %(message)s' + reset,
        logging.WARNING: yellow + '%(levelname)s: %(message)s' + reset,
        logging.ERROR: red + '%(levelname)s: %(message)s' + reset,
        logging.CRITICAL: bold_red + '%(levelname)s: %(message)s' + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging(app):
    if not app.debug:
        import os
        # Ensure log directory exists
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File Handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'SFarming.log'),
            maxBytes=10240,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Console Handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('SFarming startup')
