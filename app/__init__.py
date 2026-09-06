import sys
import traceback
from flask import Flask, render_template, redirect, url_for, request, send_from_directory, make_response
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv
from app.config import Config
from app.translations import t as t_func
from app.utils.logger import setup_logging, before_request_logger, after_request_logger, log_exception

__version__ = '0.9.17'

bootstrap = Bootstrap()


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def create_app():
    try:
        app = Flask(__name__)
        app.config.from_object(Config)
        
        bootstrap.init_app(app)
        
        logger = setup_logging(app)
        
        app.jinja_env.globals['t'] = t_func
        app.jinja_env.globals['app_version'] = __version__
        
        if logger:
            app.before_request(before_request_logger)
            app.after_request(after_request_logger)
        
        @app.route('/static/css/custom.css')
        def custom_css():
            response = make_response(send_from_directory(app.static_folder, 'css/custom.css'))
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response

        @app.errorhandler(404)
        @log_exception
        def not_found_error(error):
            try:
                if logger:
                    logger.error(f'404 Not Found: {error}')
                return render_template('404.html'), 404
            except Exception as e:
                return f'404 Not Found: {error}', 404
        
        @app.errorhandler(500)
        @log_exception
        def internal_error(error):
            try:
                if logger:
                    logger.error(f'500 Internal Server Error: {error}', exc_info=True)
                return render_template('500.html'), 500
            except Exception as e:
                return f'500 Internal Server Error: {error}', 500
        
        @app.errorhandler(Exception)
        @log_exception
        def handle_exception(error):
            try:
                if logger:
                    logger.error(f'Unhandled Exception: {str(error)}', exc_info=True)
                return render_template('500.html'), 500
            except Exception as e:
                return f'Server Error: {error}', 500
        
        @app.route('/')
        @log_exception
        def index():
            try:
                from flask import session
                if 'user_id' in session:
                    return redirect(url_for('dashboard.index'))
                return redirect(url_for('auth.login'))
            except Exception as e:
                err = _error_info(e)
                if logger:
                    logger.error(f"Index route error: {err['message']} at line {err['line']}", exc_info=True)
                return f'Index route error: {err["message"]}', 500
        
        from app.blueprints.auth import auth_bp
        from app.blueprints.dashboard import dashboard_bp
        from app.blueprints.farms import farms_bp
        from app.blueprints.activities import activities_bp
        from app.blueprints.users import users_bp
        from app.blueprints.sectors import sectors_bp
        from app.blueprints.zones import zones_bp
        from app.blueprints.rows import rows_bp
        from app.blueprints.trees import trees_bp
        from app.blueprints.visits import visits_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(farms_bp)
        app.register_blueprint(activities_bp)
        app.register_blueprint(users_bp)
        app.register_blueprint(sectors_bp)
        app.register_blueprint(zones_bp)
        app.register_blueprint(rows_bp)
        app.register_blueprint(trees_bp)
        app.register_blueprint(visits_bp)

        return app
    except Exception as e:
        err = _error_info(e)
        print(f"[FATAL] create_app failed: {err['message']} at line {err['line']}", file=sys.stderr)
        print(err['trace'], file=sys.stderr)
        raise
