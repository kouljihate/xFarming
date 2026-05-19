from app.utils.logger import (
    setup_logging,
    get_logger,
    log_action,
    log_message,
    log_function_call,
    log_with_context,
    log_exception,
    before_request_logger,
    after_request_logger,
    _error_info,
    _get_caller_info,
    log_activity
)

from functools import wraps
from flask import session, redirect, url_for, flash


def log_func_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return log_with_context('CALL', 'FUNCTION')(func)(*args, **kwargs)
    return wrapper


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if 'user_id' not in session:
                flash('Please log in first', 'warning')
                return redirect(url_for('auth.login'))
            return func(*args, **kwargs)
        except Exception as e:
            err = _error_info(e)
            flash(f'Login error: {err["message"]}', 'danger')
            return redirect(url_for('auth.login'))
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if 'user_id' not in session:
                flash('Please log in first', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') != 'admin':
                flash('Admin access required', 'danger')
                from flask import request
                return redirect(request.referrer or url_for('dashboard.index'))
            return func(*args, **kwargs)
        except Exception as e:
            err = _error_info(e)
            flash(f'Admin check error: {err["message"]}', 'danger')
            return redirect(url_for('dashboard.index'))
    return wrapper


def get_logs(page=1, per_page=50, level=None):
    try:
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
    except Exception as e:
        return _error_info(e), 0