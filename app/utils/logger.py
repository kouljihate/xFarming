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

_old_factory = logging.getLogRecordFactory()
def _record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    record.app_name = APP_NAME
    record.user = 'system'
    record.action = 'SYSTEM'
    record.action_type = 'NONE'
    record.func_name = 'unknown'
    record.line_no = 0
    return record
logging.setLogRecordFactory(_record_factory)


class ContextFilter(logging.Filter):
    def __init__(self, app_name=APP_NAME):
        super().__init__()
        self.app_name = app_name

    def filter(self, record):
        try:
            record.app_name = self.app_name
            record.user = session.get('username', 'anonymous') if 'username' in session else 'anonymous'
            if hasattr(record, '_action'):
                record.action = record._action
            if hasattr(record, '_action_type'):
                record.action_type = record._action_type
            if hasattr(record, '_func_name'):
                record.func_name = record._func_name
            if hasattr(record, '_line_no'):
                record.line_no = record._line_no
        except Exception:
            pass
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
            '_action': action or 'SYSTEM',
            '_action_type': action_type or 'NONE',
            '_func_name': _get_caller_info(3)['func'],
            '_line_no': line_no or _get_caller_info(3)['line']
        }
        
        if level == 'error':
            extra['_line_no'] = line_no or _get_caller_info(2)['line']
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
                '_action': 'CALL',
                '_action_type': 'FUNCTION',
                '_func_name': f"{module}.{func.__name__}",
                '_line_no': caller['line']
            }
            logger.debug(f"Entering: {module}.{func.__name__}()", extra=extra)
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting: {module}.{func.__name__}()", extra=extra)
                return result
            except Exception as e:
                tb = traceback.format_exc()
                caller_exc = _get_caller_info(2)
                extra['_line_no'] = caller_exc['line']
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
                    '_action': action,
                    '_action_type': action_type,
                    '_func_name': f"{module}.{func.__name__}",
                    '_line_no': caller['line']
                }
                
                logger.log(
                    logging._nameToLevel.get(level.upper(), logging.INFO),
                    f"Executing: {module}.{func.__name__}() - {action}",
                    extra=extra
                )
                
                try:
                    result = func(*args, **kwargs)
                    logger.log(
                        logging._nameToLevel.get(level.upper(), logging.INFO),
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
                '_action': 'EXCEPTION',
                '_action_type': 'ERROR',
                '_func_name': f"{module}.{func.__name__}",
                '_line_no': caller['line']
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
                '_action': f'{method} {path}',
                '_action_type': 'HTTP_REQUEST',
                '_func_name': endpoint,
                '_line_no': 0
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
                extra['_line_no'] = caller['line']
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
            '_action': f'{request.method} {request.path}',
            '_action_type': 'HTTP_REQUEST',
            '_func_name': request.endpoint or 'unknown',
            '_line_no': 0
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
            '_action': f'{request.method} {request.path}',
            '_action_type': 'HTTP_RESPONSE',
            '_func_name': request.endpoint or 'unknown',
            '_line_no': 0
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
            '_action': 'LOG',
            '_action_type': 'MESSAGE',
            '_func_name': caller.get('func', 'unknown'),
            '_line_no': caller.get('line', 0)
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