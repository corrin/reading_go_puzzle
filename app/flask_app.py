from flask import Flask
from flask import Blueprint, render_template
from flask_login import LoginManager

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config.from_object('config.Config')

    login_manager.init_app(app)

    # Register blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
else:
    # This block will be executed when running on PythonAnywhere
    application_func = app
