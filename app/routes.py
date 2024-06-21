from flask import Blueprint, redirect, url_for, request, render_template
from flask_login import login_user, current_user, login_required
from flask import redirect, url_for, session, request

from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app import db
from app.db import AccessLog
from app.models import User
from datetime import datetime
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
        credentials = Credentials.from_authorized_user_info(info=request.get_json())
        # Extract user information from the POST request
        user_info = request.json.get('user_info')
        email = user_info.get('email')

        # Check if the user already exists in the database
        user = User.query.filter_by(email=email).first()

        if not user:
            # Create a new user
            user = User(email=email)
            db.session.add(user)
            db.session.commit()
        else:
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()

        # Log the login attempt
        login_log = AccessLog(user_id=user.id,page='/google_login')
        db.session.add(login_log)
        db.session.commit()

        # Log in the user
        login_user(user)

        # Store the credentials in the session for later use
        session['credentials'] = credentials_to_dict(credentials)

        return redirect(url_for('main.dashboard'))

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
