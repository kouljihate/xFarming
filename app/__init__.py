from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv
import os
from app.config import Config
from app.translations import t as t_func

__version__ = '0.7.20'

bootstrap = Bootstrap()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    bootstrap.init_app(app)
    
    app.jinja_env.globals['t'] = t_func
    app.jinja_env.globals['app_version'] = __version__
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.route('/')
    def index():
        from flask import session
        if 'user_id' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.lands import lands_bp
    from app.blueprints.activities import activities_bp
    from app.blueprints.users import users_bp
    from app.blueprints.sectors import sectors_bp
    from app.blueprints.zones import zones_bp
    from app.blueprints.rows import rows_bp
    from app.blueprints.trees import trees_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(lands_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(sectors_bp)
    app.register_blueprint(zones_bp)
    app.register_blueprint(rows_bp)
    app.register_blueprint(trees_bp)
    
    return app
