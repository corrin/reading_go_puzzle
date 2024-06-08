from flask import Blueprint, redirect, url_for, request, render_template
from flask_login import login_user, current_user, login_required
from flask import redirect, url_for, session, request

from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


from app.models import User
from app.logger import logger

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


def main_bp(app):
    bp = Blueprint('main', __name__)

    @bp.route('/')
    def index():
        if current_user.is_authenticated:
            # User is already logged in
            return redirect(url_for('main.dashboard'))
        else:
            # Render the login page with the "Log in with Google" button
            return render_template('login.html', google_client_id=app.config['GOOGLE_CLIENT_ID'])

    @bp.route('/google_login', methods=['POST'])
    def google_login():
        # Get the user's credentials from the Google Sign-In response
        credentials = Credentials.from_authorized_user_info(info=request.get_json())

        # Store the credentials in the session for later use
        session['credentials'] = credentials_to_dict(credentials)

        # Redirect the user to the desired page after successful sign-in
        return redirect(url_for('main.dashboard'))

        auth_url, _ = flow.authorization_url(prompt='consent')
        logger.debug(f"Redirecting to Google OAuth URL: {auth_url}")
        return redirect(auth_url)

    @bp.route('/callback')
    def callback():
        flow = Flow.from_client_config(
            client_config={
                'web': {
                    'client_id': app.config['GOOGLE_CLIENT_ID'],
                    'client_secret': app.config['GOOGLE_CLIENT_SECRET'],
                    'redirect_uris': ['http://localhost:5000/callback'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token'
                }
            },
            scopes=['openid', 'email', 'profile']
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        # Use the credentials to get user information and complete the sign-in process
        # ...

    @bp.route('/privacy')
    def privacy():
        return render_template('privacy.html')

    @bp.route('/tos')
    def tos():
        return render_template('tos.html')

    @bp.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    return bp
