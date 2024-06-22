from flask import Blueprint, redirect, url_for, request, render_template, jsonify
from flask_login import login_user, current_user, login_required
from flask import redirect, url_for, session, request

from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app.db import db, AccessLog
from app.user import User
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
        logger.debug("Hello")
        logger.info("Google login function called")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request data: {request.data}")

        try:
            json_data = request.get_json()
            logger.info(f"JSON data: {json_data}")
            user_info = json_data.get('user_info')
            if not user_info:
                raise ValueError("User info is missing in the request")

            email = user_info.get('email')
            if not email:
                raise ValueError("Email is missing in the user info")

            logger.info(f"Searching for user with email: {email}")

            # Check if the user already exists in the database
            user = User.query.filter_by(email=email).first()
            logger.info(f"User query result: {user}")

            if not user:
                # Create a new user
                user = User(email=email)
                db.session.add(user)
                db.session.commit()
                logger.info("New user created and committed to database")
            else:
                # Update last login time
                logger.info("Updating existing user's last login time")
                user.last_login = datetime.utcnow()
                db.session.commit()
                logger.info("User last login time updated and committed to database")

            # Log the login
            logger.info("Creating AccessLog entry")
            login_log = AccessLog(user_id=user.id,page='/google_login')
            db.session.add(login_log)
            db.session.commit()
            logger.info("AccessLog entry created and committed to database")

            # Log in the user
            logger.info("Logging in user")
            login_user(user, remember=True)
            logger.info("User logged in successfully")
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            logger.error(f"Error in google_login: {str(e)}")
            return jsonify({"error": str(e)}), 400

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
