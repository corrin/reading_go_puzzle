from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class AccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    page = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<AccessLog user_id={self.user_id} access_time={self.access_time} page={self.page}>'
