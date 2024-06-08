import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TEMPLATES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    GOOGLE_REDIRECT_URI = 'https://0c8d-202-169-216-166.ngrok-free.app/callback'
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
