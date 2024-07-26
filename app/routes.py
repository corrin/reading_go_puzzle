from flask_login import login_user, current_user, login_required, logout_user
from flask import Blueprint, render_template, jsonify, flash
from flask import redirect, url_for, session, request
from flask import current_app

from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from sqlalchemy.exc import NoResultFound

from app.challenge import Challenge, Response
from app.challenge_manager import ChallengeManager
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

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    logger.debug(f"GOOGLE_CLIENT_ID in root route: {current_app.config.get('GOOGLE_CLIENT_ID')}")
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('main.login'))

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

        credential = json_data['user_info']['credential']

        client_id = current_app.config.get('GOOGLE_CLIENT_ID')

        # Verify the JWT
        id_info = id_token.verify_oauth2_token(credential, google_auth_requests.Request(), client_id)

        email = id_info.get('email')
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

        # Store profile info in Flask session
        session['user_profile'] = {
            'name': id_info.get('name'),
            'picture': id_info.get('picture')
        }

        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')

        logger.info(f"Debug - Email: {email}, Name: {name}, Picture URL: {picture}")

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
    user_profile = session.get('user_profile', {})
    logger.info(f"Debug - Dashboard User Profile: {user_profile}")  # Debug print
    return render_template('dashboard.html')


@bp.route('/login')
def login():
    logger.debug(f"GOOGLE_CLIENT_ID in login route: {current_app.config.get('GOOGLE_CLIENT_ID')}")
    return render_template('login.html', google_client_id=current_app.config['GOOGLE_CLIENT_ID'])

@bp.route('/logout')
@login_required
def logout():
    session.pop('user_profile', None)  # Clear the profile info from Flask session
    logout_user()
    return redirect(url_for('main.index'))
@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/play')
@login_required
def play():
    try:
        new_challenge = ChallengeManager.create_new_challenge(current_user.id)
        session['current_challenge_id'] = new_challenge.id
        return redirect(url_for('main.problem', challenge_id=new_challenge.id, problem_index=0))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/problem/<challenge_id>/<int:problem_index>')
@login_required
def problem(challenge_id, problem_index):
    challenge = Challenge.query.get_or_404(challenge_id)
    problem = challenge.get_problem(problem_index)
    if problem is None:
        return redirect(url_for('main.dashboard'))

    return render_template('problem.html', problem=problem, challenge_id=challenge_id, problem_index=problem_index, total_problems=len(challenge.problems))

@bp.route('/submit_response', methods=['POST'])
@login_required
def submit_response():
    data = request.get_json()
    challenge_id = data.get('challenge_id')
    problem_index = data.get('problem_index')
    user_response = data.get('response')

    challenge = Challenge.query.get_or_404(challenge_id)
    problem = challenge.get_problem(problem_index)

    is_correct = user_response == problem.correct_response

    response = Response(
        challenge_id=challenge_id,
        problem_id=problem.id,
        user_response=user_response,
        is_correct=is_correct
    )
    db.session.add(response)
    db.session.commit()

    # Update the challenge's current problem index
    challenge.current_problem_index = problem_index + 1
    db.session.commit()

    return jsonify({"success": True})

