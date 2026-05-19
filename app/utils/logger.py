import sys
import os
import logging
import traceback
import functools
from datetime import datetime
from logging.config import dictConfig
from functools import wraps

from flask import request, session, g, current_app
from app.utils.logger_config import LOGGING_CONFIG, APP_NAME, LOG_MODE


class ContextFilter(logging.Filter):
    def __init__(self, app_name=APP_NAME):
        super().__init__()
        self.app_name = app_name

    def filter(self, record):
        try:
            record.app_name = self.app_name
            record.user = session.get('username', 'anonymous') if 'username' in session else 'anonymous'
            record.action = getattr(record, 'action', 'SYSTEM')
            record.action_type = getattr(record, 'action_type', 'NONE')
            record.func_name = getattr(record, 'func_name', 'unknown')
            record.line_no = getattr(record, 'line_no', 0)
        except Exception:
            record.app_name = self.app_name
            record.user = 'unknown'
            record.action = 'SYSTEM'
            record.action_type = 'NONE'
            record.func_name = 'unknown'
            record.line_no = 0
        return True


def setup_logging(app):
    try:
        os.makedirs(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'), exist_ok=True)
        dictConfig(LOGGING_CONFIG)
        logger = logging.getLogger('app')
        logger.addFilter(ContextFilter(APP_NAME))
        app.logger = logger
        logger.info(f'{APP_NAME} startup - Log mode: {LOG_MODE}')
        return logger
    except Exception as e:
        print(f"[FATAL] setup_logging failed: {e}", file=sys.stderr)
        traceback.print_exc()
        return None


def get_logger(name='app'):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addFilter(ContextFilter(APP_NAME))
    return logger


def _get_caller_info(depth=2):
    try:
        frame = sys._getframe(depth)
        filename = os.path.basename(frame.f_code.co_filename)
        func_name = frame.f_code.co_name
        line_no = frame.f_lineno
        return {'file': filename, 'func': func_name, 'line': line_no}
    except Exception:
        return {'file': 'unknown.py', 'func': 'unknown', 'line': 0}


def _log_message(logger, level, action, action_type, description, line_no=None):
    try:
        extra = {
            'action': action or 'SYSTEM',
            'action_type': action_type or 'NONE',
            'func_name': _get_caller_info(3)['func'],
            'line_no': line_no or _get_caller_info(3)['line']
        }
        
        if level == 'error':
            extra['line_no'] = line_no or _get_caller_info(2)['line']
            logger.error(description, extra=extra)
        elif level == 'warning':
            logger.warning(description, extra=extra)
        elif level == 'debug':
            logger.debug(description, extra=extra)
        else:
            logger.info(description, extra=extra)
    except Exception as e:
        print(f"[LOG ERROR] Failed to log: {e}", file=sys.stderr)


def log_action(action, action_type, description, level='info'):
    try:
        logger = get_logger('app')
        _log_message(logger, level, action, action_type, description)
    except Exception:
        pass


def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger = get_logger('app')
            caller = _get_caller_info(2)
            module = func.__module__ or 'unknown'
            
            extra = {
                'action': 'CALL',
                'action_type': 'FUNCTION',
                'func_name': f"{module}.{func.__name__}",
                'line_no': caller['line']
            }
            logger.debug(f"Entering: {module}.{func.__name__}()", extra=extra)
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting: {module}.{func.__name__}()", extra=extra)
                return result
            except Exception as e:
                tb = traceback.format_exc()
                caller_exc = _get_caller_info(2)
                extra['line_no'] = caller_exc['line']
                logger.error(
                    f"Error in {module}.{func.__name__}(): {str(e)} | Line: {caller_exc['line']} | Trace: {tb}",
                    extra=extra
                )
                raise
        except Exception as e:
            raise
    return wrapper


def log_with_context(action, action_type, level='info'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger = get_logger('app')
                caller = _get_caller_info(2)
                module = func.__module__ or 'unknown'
                
                extra = {
                    'action': action,
                    'action_type': action_type,
                    'func_name': f"{module}.{func.__name__}",
                    'line_no': caller['line']
                }
                
                logger.log(
                    logging._levelToName.get(getattr(logging, level.upper(), logging.INFO)),
                    f"Executing: {module}.{func.__name__}() - {action}",
                    extra=extra
                )
                
                try:
                    result = func(*args, **kwargs)
                    logger.log(
                        logging._levelToName.get(getattr(logging, level.upper(), logging.INFO)),
                        f"Completed: {module}.{func.__name__}() - {action}",
                        extra=extra
                    )
                    return result
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(
                        f"Failed: {module}.{func.__name__}() - {action} | Error: {str(e)} | Line: {caller['line']} | Trace: {tb}",
                        extra=extra
                    )
                    raise
            except Exception as e:
                raise
        return wrapper
    return decorator


def log_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = get_logger('app')
            caller = _get_caller_info(2)
            module = func.__module__ or 'unknown'
            tb = traceback.format_exc()
            
            extra = {
                'action': 'EXCEPTION',
                'action_type': 'ERROR',
                'func_name': f"{module}.{func.__name__}",
                'line_no': caller['line']
            }
            logger.error(
                f"Exception in {module}.{func.__name__}(): {str(e)} | Line: {caller['line']} | Trace: {tb}",
                extra=extra
            )
            raise
    return wrapper


def log_request(request_handler):
    @wraps(request_handler)
    def wrapper(*args, **kwargs):
        try:
            logger = get_logger('app')
            endpoint = request.endpoint or 'unknown'
            method = request.method
            path = request.path
            user = session.get('username', 'anonymous')
            
            extra = {
                'action': f'{method} {path}',
                'action_type': 'HTTP_REQUEST',
                'func_name': endpoint,
                'line_no': 0
            }
            
            logger.info(
                f"Request: {method} {path} | User: {user} | Endpoint: {endpoint}",
                extra=extra
            )
            
            try:
                response = request_handler(*args, **kwargs)
                logger.info(
                    f"Response: {method} {path} | Status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}",
                    extra=extra
                )
                return response
            except Exception as e:
                tb = traceback.format_exc()
                caller = _get_caller_info(2)
                extra['line_no'] = caller['line']
                logger.error(
                    f"Request Error: {method} {path} | Error: {str(e)} | Line: {caller['line']} | Trace: {tb}",
                    extra=extra
                )
                raise
        except Exception as e:
            raise
    return wrapper


def before_request_logger():
    try:
        g.request_start_time = datetime.utcnow()
        logger = get_logger('app')
        
        extra = {
            'action': f'{request.method} {request.path}',
            'action_type': 'HTTP_REQUEST',
            'func_name': request.endpoint or 'unknown',
            'line_no': 0
        }
        logger.info(
            f"Start: {request.method} {request.path} | User: {session.get('username', 'anonymous')}",
            extra=extra
        )
    except Exception:
        pass


def after_request_logger(response):
    try:
        logger = get_logger('app')
        duration = (datetime.utcnow() - g.get('request_start_time', datetime.utcnow())).total_seconds()
        
        extra = {
            'action': f'{request.method} {request.path}',
            'action_type': 'HTTP_RESPONSE',
            'func_name': request.endpoint or 'unknown',
            'line_no': 0
        }
        logger.info(
            f"End: {request.method} {request.path} | Status: {response.status_code} | Duration: {duration:.3f}s",
            extra=extra
        )
    except Exception:
        pass
    return response


def log_activity(user_id, action, description, level='info'):
    try:
        from app.database import get_db
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            return
        
        activity_log = {
            'user_id': user_id,
            'action': action,
            'description': description,
            'level': level,
            'timestamp': datetime.utcnow(),
            'ip_address': request.remote_addr if request else None
        }
        db.activities.insert_one(activity_log)
    except Exception:
        pass


def log_message(level, message, user_id=None, username=None, caller_info=None):
    try:
        logger = get_logger('app')
        caller = caller_info or _get_caller_info(2)
        
        extra = {
            'action': 'LOG',
            'action_type': 'MESSAGE',
            'func_name': caller.get('func', 'unknown'),
            'line_no': caller.get('line', 0)
        }
        
        level_map = {
            'debug': logger.debug,
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }
        
        log_func = level_map.get(level.lower(), logger.info)
        log_func(message, extra=extra)
        
    except Exception as e:
        print(f"[LOG ERROR] Failed to log message: {e}", file=sys.stderr)


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }