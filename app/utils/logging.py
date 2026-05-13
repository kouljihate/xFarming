import os
import logging
import sys
import functools
from datetime import datetime

from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(func):
    """Decorator to require user login"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    """Decorator to require admin role"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            from flask import request
            return redirect(request.referrer or url_for('dashboard.index'))
        return func(*args, **kwargs)
    return wrapper

def log_func_call(func):
    """Decorator to log function calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import current_app
        try:
            current_app.logger.debug(f"Calling function: {func.__module__}.{func.__name__}")
        except:
            pass
        return func(*args, **kwargs)
    return wrapper

def log_message(level, message, user_id=None, username=None):
    """
    Log a message to MongoDB logs collection and Flask logger.
    Levels: 'info', 'warning', 'error'
    """
    import sys
    from app.database import get_db
    from flask import current_app
    
    print(f"[LOG-{level.upper()}] {message}", file=sys.stdout)
    
    if level not in ['info', 'warning', 'error']:
        level = 'info'
    
    try:
        db = get_db()
        log_entry = {
            'level': level,
            'message': message,
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'username': username
        }
        db.logs.insert_one(log_entry)
    except Exception as e:
        pass
     
    try:
        if level == 'error':
            current_app.logger.error(message)
        elif level == 'warning':
            current_app.logger.warning(message)
        else:
            current_app.logger.info(message)
    except Exception as e:
        pass

def get_logs(page=1, per_page=50, level=None):
    from app.database import get_db
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
    log_mode = os.environ.get('LOG_MODE', 'file')
    
    if not app.debug:
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'SmartFarmerFlow.log')
        
        if log_mode == 'console':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(ColorFormatter(
                '%(asctime)s %(levelname)s: %(message)s'
            ))
            console_handler.setLevel(logging.DEBUG)
            app.logger.addHandler(console_handler)
            app.logger.setLevel(logging.DEBUG)
            
        elif log_mode == 'file':
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10240,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            
        else:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10240,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(ColorFormatter(
                '%(asctime)s %(levelname)s: %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            app.logger.addHandler(console_handler)
            app.logger.setLevel(logging.INFO)
        
        app.logger.info(f'SmartFarmerFlow startup - Log mode: {log_mode}')