import os

from werkzeug.middleware.proxy_fix import ProxyFix  # Just in dev to handle ngrok
from flask import Flask, session
from flask_login import LoginManager
from app.logger import logger
from app.db import db
from app.user import User
from config import Config
from app.routes import bp as main_bp
from app.problem import Problem
from flask_migrate import Migrate

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Just in dev to handle ngrok

    logger.info(f"App instance path (before loading config): {app.instance_path}")

    app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

    # Configure the app
    app.config.from_object('config.Config')
    logger.info(f"App instance path (after loading config): {app.instance_path}")

    print(f"GOOGLE_CLIENT_ID: {app.config.get('GOOGLE_CLIENT_ID')}")
    print(f"Remember to use ngrok:  https://measured-enormously-man.ngrok-free.app -> http://localhost:5000")

    #logger.info(f"App config: {app.config}")

    app.template_folder = app.config['TEMPLATE_FOLDER']
    app.static_folder = app.config['STATIC_FOLDER']

    db.init_app(app)
    login_manager.init_app(app)


    # Register blueprints
    app.register_blueprint(main_bp)

    # Add context processor
    @app.context_processor
    def inject_user_profile():
        return dict(user_profile=session.get('user_profile', {}))

    with app.app_context():
        db.create_all()
        Problem.load_sgf_files()

    return app


# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)  # Updated to query the database

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
else:
    # This block will be executed when running on PythonAnywhere
    application_func = app