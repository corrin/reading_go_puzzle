import random
from app.db import db
from app.challenge import Challenge
from app.problem import Problem

class ChallengeManager:
    @staticmethod
    def create_new_challenge(user_id):
        # Select 20 problems semi-randomly for now
        problem_ids = [problem.id for problem in Problem.query.all()]
        selected_problems = random.sample(problem_ids, 20)

        # Create a new challenge
        new_challenge = Challenge(user_id=user_id, problems=selected_problems)
        db.session.add(new_challenge)
        db.session.commit()

        return new_challenge
