import numpy as np
from typing import List, Dict, Any, Optional
import logging
import random

from models.mock_interview import (
    Question,
    QuestionType,
    DifficultyLevel,
    ThompsonSamplingParams,
    InterviewSession,
)

logger = logging.getLogger(__name__)


class ThompsonSamplingService:
    def __init__(self):
        self.thompson_params = ThompsonSamplingParams()

    def initialize_thompson_sampling(
        self, session: InterviewSession, job_requirements: Dict[str, Any]
    ):
        """Initialize Thompson Sampling parameters based on job requirements"""
        # Extract skills and requirements from job description
        key_skills = job_requirements.get("key_skills", [])
        experience_level = job_requirements.get("experience_level", "intermediate")

        # Initialize question type parameters based on job requirements
        for q_type in [
            QuestionType.TECHNICAL,
            QuestionType.BEHAVIORAL,
            QuestionType.PROBLEM_SOLVING,
            QuestionType.CULTURAL_FIT,
        ]:
            # Higher initial success for technical questions if tech-heavy job
            if q_type == QuestionType.TECHNICAL and len(key_skills) > 3:
                self.thompson_params.question_type_success[q_type] = 3
                self.thompson_params.question_type_failure[q_type] = 1
            else:
                self.thompson_params.question_type_success[q_type] = 2
                self.thompson_params.question_type_failure[q_type] = 2

        # Initialize difficulty parameters based on experience level
        difficulty_mapping = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
            "expert": DifficultyLevel.EXPERT,
        }

        target_difficulty = difficulty_mapping.get(
            experience_level, DifficultyLevel.INTERMEDIATE
        )

        for diff in [
            DifficultyLevel.BEGINNER,
            DifficultyLevel.INTERMEDIATE,
            DifficultyLevel.ADVANCED,
            DifficultyLevel.EXPERT,
        ]:
            if diff == target_difficulty:
                self.thompson_params.difficulty_success[diff] = 3
                self.thompson_params.difficulty_failure[diff] = 1
            else:
                self.thompson_params.difficulty_success[diff] = 2
                self.thompson_params.difficulty_failure[diff] = 2

    def update_thompson_params(self, answer, question):
        """Update Thompson sampling parameters based on answer performance"""
        # Update question type parameters
        if answer.technical_score >= 0.7:  # Good answer
            self.thompson_params.question_type_success[question.type] = (
                self.thompson_params.question_type_success.get(question.type, 0) + 1
            )
        else:  # Poor answer
            self.thompson_params.question_type_failure[question.type] = (
                self.thompson_params.question_type_failure.get(question.type, 0) + 1
            )

        # Update difficulty parameters
        if answer.technical_score >= 0.7:
            self.thompson_params.difficulty_success[question.difficulty] = (
                self.thompson_params.difficulty_success.get(question.difficulty, 0) + 1
            )
        else:
            self.thompson_params.difficulty_failure[question.difficulty] = (
                self.thompson_params.difficulty_failure.get(question.difficulty, 0) + 1
            )
