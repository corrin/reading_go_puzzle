import hashlib
import os
from app.db import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sgfmill import sgf
from flask import current_app


class Problem(db.Model):
    __tablename__ = 'problem'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hash = db.Column(db.String(64), unique=True, nullable=False)  # New hash column
    problem_type = db.Column(db.String(50), nullable=False)
    board_image = db.Column(db.String(256), nullable=False)
    color_to_move = db.Column(db.String(10), nullable=False)
    correct_response_play = db.Column(db.String(20), nullable=False)
    correct_response_tenuki = db.Column(db.String(20), nullable=False)
    sgf_content = db.Column(db.Text, nullable=False)

    @staticmethod
    def generate_hash(sgf_content):
        return hashlib.sha256(sgf_content.encode()).hexdigest()

    def __init__(self, problem_type, board_image, color_to_move, correct_response_play, correct_response_tenuki,
                 sgf_content):
        self.hash = self.generate_hash(sgf_content)
        self.problem_type = problem_type
        self.board_image = board_image
        self.color_to_move = color_to_move
        self.correct_response_play = correct_response_play
        self.correct_response_tenuki = correct_response_tenuki
        self.sgf_content = sgf_content

    @classmethod
    def load_sgf_files(cls):
        sgf_dir = os.path.join(current_app.root_path, '..', 'sgf', 'processed')
        loaded_count = 0
        for filename in os.listdir(sgf_dir):
            if filename.endswith('.sgf'):
                file_path = os.path.join(sgf_dir, filename)
                try:
                    with open(file_path, 'rb') as f:
                        sgf_content = f.read().decode('utf-8')

                    # Generate hash
                    file_hash = cls.generate_hash(sgf_content)

                    # Check if problem with this hash already exists
                    if cls.query.filter_by(hash=file_hash).first():
                        current_app.logger.info(f"Problem already exists, skipping: {filename}")
                        os.remove(file_path)  # Remove duplicate file
                        continue

                    # Parse SGF file
                    game = sgf.Sgf_game.from_bytes(sgf_content.encode())
                    root = game.get_root()

                    # Extract necessary information
                    problem_type = 'tsumego'  # Assuming all are tsumego problems for now
                    board_image = filename  # Using filename as board image for now
                    color_to_move = root.get('PL')[0].lower()
                    correct_response = 'YES' if 'Correct answer: YES' in root.get('C')[0] else 'NO'

                    # Create Problem instance
                    problem = cls(
                        problem_type=problem_type,
                        board_image=board_image,
                        color_to_move=color_to_move,
                        correct_response_play=correct_response,
                        correct_response_tenuki='NO' if correct_response == 'YES' else 'YES',
                        sgf_content=sgf_content
                    )

                    db.session.add(problem)
                    db.session.commit()
                    loaded_count += 1

                    # Delete the file after successful processing
                    os.remove(file_path)
                    current_app.logger.info(f"Loaded and deleted: {filename}")

                except Exception as e:
                    current_app.logger.error(f"Error processing {filename}: {str(e)}")

        current_app.logger.info(f"Loaded {loaded_count} new problems into the database.")
        current_app.logger.info(f"Total problems in database: {cls.query.count()}")