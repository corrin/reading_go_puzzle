import hashlib
from app.db import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.problem import Problem

class Challenge(db.Model):
    __tablename__ = 'challenge'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problems = db.Column(db.PickleType, nullable=False)
    current_problem_index = db.Column(db.Integer, default=0)
    responses = db.relationship('Response', backref='challenge', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def generate_uuid(problem_ids):
        concatenated_ids = ''.join(str(pid) for pid in problem_ids)
        return uuid.UUID(hashlib.md5(concatenated_ids.encode()).hexdigest())

    def __init__(self, user_id, problems):
        self.id = self.generate_uuid(problems)
        self.user_id = user_id
        self.problems = problems

    def get_problem(self, problem_index):
        if problem_index >= len(self.problems) or problem_index < 0:
            return None

        problem_id = self.problems[problem_index]
        problem = Problem.query.get_or_404(problem_id)

        return problem

class Response(db.Model):
    __tablename__ = 'response'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(UUID(as_uuid=True), db.ForeignKey('challenge.id'), nullable=False)
    problem_id = db.Column(UUID(as_uuid=True), db.ForeignKey('problem.id'), nullable=False)
    user_response_play = db.Column(db.String(20), nullable=False)
    user_response_tenuki = db.Column(db.String(20), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
