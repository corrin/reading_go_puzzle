from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from app.db import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=True)
    profile_pic = db.Column(db.String(200), nullable=True)
    last_login = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, email, name=None, profile_pic=None, last_login=None):
        self.email = email
        self.name = name
        self.profile_pic = profile_pic
        self.last_login = last_login or datetime.utcnow()

    def get_id(self):
        return self.id  # Return the primary key

    def __repr__(self):
        return f'<User {self.email}>'
