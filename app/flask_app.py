import os

from flask import Flask
from flask_login import LoginManager
from app.models import User
from app.logger import logger
from app.db import db, User

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, instance_relative_config=False)

    logger.info(f"App instance path (before loading config): {app.instance_path}")

    app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

    # Configure the app
    app.config.from_object('config.Config')
    logger.info(f"App instance path (after loading config): {app.instance_path}")
    #logger.info(f"App config: {app.config}")

    app.template_folder = app.config['TEMPLATES_FOLDER']

    db.init_app(app)
    logger.debug("Database initialised")
    login_manager.init_app(app)


    # Register blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp(app))

    with app.app_context():
        logger.debug("Creating all database tables...")
        db.create_all()
        logger.info("Database tables created or verified")

    db_path = os.path.abspath(app.config['SQLALCHEMY_DATABASE_URI'].replace("sqlite:///", ""))
    logger.debug(f"Expected database path: {db_path}")
    if os.path.exists(db_path):
        logger.info(f"Database file '{db_path}' exists.")
    else:
        logger.error(f"Database file '{db_path}' does not exist.")


    return app

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
else:
    # This block will be executed when running on PythonAnywhere
    application_func = app