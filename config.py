import os
from dotenv import load_dotenv
from app.logger import logger  # Assuming logger is defined in app/logger.py

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))

    TEMPLATE_FOLDER = os.path.join(basedir, 'templates')
    STATIC_FOLDER = os.path.join(basedir, 'static')

    GOOGLE_REDIRECT_URI = 'https://0c8d-202-169-216-166.ngrok-free.app/callback'
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    PREFERRED_URL_SCHEME = 'https'

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'tsumego.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

logger.info(f"SQLALCHEMY_DATABASE_URI: {Config.SQLALCHEMY_DATABASE_URI}")
