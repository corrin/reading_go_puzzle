import hashlib
from app.db import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Problem(db.Model):
    __tablename__ = 'problem'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_type = db.Column(db.String(50), nullable=False)  # Can be 'tsumego', 'shicho', etc.
    board_image = db.Column(db.String(256), nullable=False)
    color_to_move = db.Column(db.String(10), nullable=False)
    correct_response_play = db.Column(db.String(20), nullable=False)
    correct_response_tenuki = db.Column(db.String(20), nullable=False)
    sgf_content = db.Column(db.Text, nullable=False)

    @staticmethod
    def generate_uuid(board_position):
        return uuid.UUID(hashlib.md5(board_position.encode()).hexdigest())

    def __init__(self, problem_type, board_image, color_to_move, correct_response_play, correct_response_tenuki, board_position):
        self.id = self.generate_uuid(board_position)
        self.problem_type = problem_type
        self.board_image = board_image
        self.color_to_move = color_to_move
        self.correct_response_play = correct_response_play
        self.correct_response_tenuki = correct_response_tenuki

    def solve(self):
        # Implement solving logic based on problem_type if needed
        pass
