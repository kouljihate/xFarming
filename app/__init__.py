from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv
import os
from app.config import Config
from app.translations import t as t_func

bootstrap = Bootstrap()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    bootstrap.init_app(app)
    
    app.jinja_env.globals['t'] = t_func
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.lands import lands_bp
    from app.blueprints.activities import activities_bp
    from app.blueprints.users import users_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(lands_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(users_bp)
    
    return app
