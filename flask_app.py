from flask import Flask

def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config.from_object('config.Config')

    # Register blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

# Create the Flask app instance
application_func = create_app
