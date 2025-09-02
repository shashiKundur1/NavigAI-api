import json
import random
import re
from typing import List, Dict, Any
from google import genai
from google.genai import types
from models.mock_interview import Question, QuestionType, DifficultyLevel
from core.settings import Settings
import logging

logger = logging.getLogger(__name__)


class QuestionGenerationService:
    def __init__(self, gemini_client=None):
        if gemini_client is not None:
            self.client = gemini_client
        else:
            if not Settings.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY is not set in the environment variables."
                )
            self.client = genai.Client(api_key=Settings.GEMINI_API_KEY)

        # Track question difficulty progression
        self.current_difficulty = DifficultyLevel.BEGINNER
        self.question_count = 0
        self.difficulty_progression = {
            DifficultyLevel.BEGINNER: 3,  # First 3 questions are beginner
            DifficultyLevel.INTERMEDIATE: 5,  # Next 5 are intermediate
            DifficultyLevel.ADVANCED: 7,  # Next 7 are advanced
            DifficultyLevel.EXPERT: 5,  # Last 5 are expert
        }

    def generate_questions_from_job_description(
        self, job_title: str, job_description: str
    ) -> List[Question]:
        """Generate initial questions from job description"""
        prompt = f"""
        Analyze this job description and generate 20 diverse interview questions for a {job_title} position:
        
        Job Description: {job_description}
        
        Generate questions with a natural progression in difficulty:
        - 3 beginner questions (warm-up, basic knowledge)
        - 5 intermediate questions (practical application)
        - 7 advanced questions (complex scenarios)
        - 5 expert questions (architecture, design patterns)
        
        For each question, provide:
        1. Question text (make it conversational and natural)
        2. Type (technical, behavioral, problem-solving, cultural_fit)
        3. Difficulty (beginner, intermediate, advanced, expert)
        4. Category
        5. Expected keywords for good answers
        
        Format as JSON array with objects containing:
        - id: unique identifier
        - text: question text
        - type: question type
        - difficulty: difficulty level
        - category: question category
        - expected_keywords: array of keywords
        
        IMPORTANT: Return ONLY valid JSON without any additional text or formatting.
        Make the questions sound like a human interviewer would ask them, not a robot.
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )

            response_text = response.text.strip()
            logger.info(f"Raw response: {response_text[:200]}...")

            # Extract JSON if it's wrapped in markdown code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
            if json_match:
                response_text = json_match.group(1)

            # Try to parse JSON
            try:
                questions_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response text: {response_text}")
                # Try to fix common JSON issues
                response_text = response_text.replace("'", '"')
                response_text = re.sub(r",\s*]", "]", response_text)
                response_text = re.sub(r",\s*}", "}", response_text)

                try:
                    questions_data = json.loads(response_text)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON even after fixes")
                    return self._get_default_questions()

            questions = []

            # Sort questions by difficulty to ensure proper progression
            difficulty_order = {
                DifficultyLevel.BEGINNER: 0,
                DifficultyLevel.INTERMEDIATE: 1,
                DifficultyLevel.ADVANCED: 2,
                DifficultyLevel.EXPERT: 3,
            }

            questions_data.sort(
                key=lambda q: difficulty_order.get(
                    q.get("difficulty", "intermediate"), 1
                )
            )

            for q_data in questions_data:
                try:
                    # Ensure all required fields are present
                    if not all(
                        key in q_data
                        for key in [
                            "id",
                            "text",
                            "type",
                            "difficulty",
                            "category",
                            "expected_keywords",
                        ]
                    ):
                        continue

                    question = Question(
                        id=q_data["id"],
                        text=q_data["text"],
                        type=q_data["type"],
                        difficulty=q_data["difficulty"],
                        category=q_data["category"],
                        expected_keywords=q_data["expected_keywords"],
                    )
                    questions.append(question)
                except Exception as e:
                    logger.error(f"Error creating question from data: {e}")
                    continue

            if not questions:
                logger.warning("No valid questions were created")
                return self._get_default_questions()

            return questions

        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return self._get_default_questions()

    def generate_contextual_next_question(
        self,
        job_description: str,
        conversation_history: List[Dict],
        asked_questions: List[str],
        candidate_performance: Dict,
    ) -> Question:
        """Generate the next question based on conversation context using advanced NLP"""

        # Update difficulty based on question count
        self._update_difficulty()

        # Format conversation history for the prompt
        history_text = ""
        for i, exchange in enumerate(
            conversation_history[-3:]
        ):  # Use last 3 exchanges for context
            history_text += f"Q{i+1}: {exchange['question']}\n"
            history_text += f"A{i+1}: {exchange['answer']}\n\n"

        # Get performance summary
        performance_summary = f"""
        Current Performance:
        - Technical Score: {candidate_performance.get('technical_score', 0.5):.2f}
        - Communication Score: {candidate_performance.get('communication_score', 0.5):.2f}
        - Confidence Score: {candidate_performance.get('confidence_score', 0.5):.2f}
        """

        # Adjust difficulty based on performance
        adjusted_difficulty = self._adjust_difficulty_based_on_performance(
            candidate_performance
        )

        prompt = f"""
        You are an expert AI interviewer conducting a mock interview for the following position:
        
        Job Description: {job_description}
        
        {performance_summary}
        
        Conversation History:
        {history_text}
        
        Already Asked Questions: {', '.join(asked_questions[-5:])}  # Show last 5 asked
        
        Generate the next question with these requirements:
        1. Difficulty level: {adjusted_difficulty.value}
        2. Make it sound natural and conversational, like a human interviewer would ask
        3. Build upon previous answers when relevant
        4. If the candidate is struggling (scores < 0.6), make the question simpler and more encouraging
        5. If the candidate is doing well (scores > 0.8), make the question more challenging
        6. Include a brief conversational transition (e.g., "Thanks for that explanation. Let's move on to...")
        7. Focus on a different aspect than the previous questions
        
        Provide the response in JSON format with:
        - id: unique identifier
        - text: the question text (include conversational transition)
        - type: question type (technical, behavioral, problem-solving, cultural_fit)
        - difficulty: difficulty level ({adjusted_difficulty.value})
        - category: question category
        - expected_keywords: array of keywords for a good answer
        
        IMPORTANT: Return ONLY valid JSON without any additional text or formatting.
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )

            # Parse the response
            response_text = response.text.strip()
            logger.info(f"Raw contextual response: {response_text[:200]}...")

            # Extract JSON if it's wrapped in markdown code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
            if json_match:
                response_text = json_match.group(1)

            # Try to parse JSON
            try:
                q_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in contextual question: {e}")
                logger.error(f"Response text: {response_text}")
                # Try to fix common JSON issues
                response_text = response_text.replace("'", '"')
                response_text = re.sub(r",\s*]", "]", response_text)
                response_text = re.sub(r",\s*}", "}", response_text)

                try:
                    q_data = json.loads(response_text)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON even after fixes")
                    return self._get_fallback_question(adjusted_difficulty)

            # Ensure all required fields are present
            if not all(
                key in q_data
                for key in [
                    "id",
                    "text",
                    "type",
                    "difficulty",
                    "category",
                    "expected_keywords",
                ]
            ):
                logger.error("Missing required fields in question data")
                return self._get_fallback_question(adjusted_difficulty)

            question = Question(
                id=q_data["id"],
                text=q_data["text"],
                type=q_data["type"],
                difficulty=q_data["difficulty"],
                category=q_data["category"],
                expected_keywords=q_data["expected_keywords"],
            )

            # Increment question count for next time
            self.question_count += 1

            return question

        except Exception as e:
            logger.error(f"Error generating contextual question: {e}")
            # Fallback to a default question
            return self._get_fallback_question(adjusted_difficulty)

    def _update_difficulty(self):
        """Update difficulty based on question count"""
        total_questions = sum(self.difficulty_progression.values())

        if self.question_count < self.difficulty_progression[DifficultyLevel.BEGINNER]:
            self.current_difficulty = DifficultyLevel.BEGINNER
        elif self.question_count < (
            self.difficulty_progression[DifficultyLevel.BEGINNER]
            + self.difficulty_progression[DifficultyLevel.INTERMEDIATE]
        ):
            self.current_difficulty = DifficultyLevel.INTERMEDIATE
        elif self.question_count < (
            self.difficulty_progression[DifficultyLevel.BEGINNER]
            + self.difficulty_progression[DifficultyLevel.INTERMEDIATE]
            + self.difficulty_progression[DifficultyLevel.ADVANCED]
        ):
            self.current_difficulty = DifficultyLevel.ADVANCED
        else:
            self.current_difficulty = DifficultyLevel.EXPERT

    def _adjust_difficulty_based_on_performance(
        self, candidate_performance: Dict
    ) -> DifficultyLevel:
        """Adjust difficulty based on candidate performance"""
        technical_score = candidate_performance.get("technical_score", 0.5)
        communication_score = candidate_performance.get("communication_score", 0.5)
        confidence_score = candidate_performance.get("confidence_score", 0.5)

        # Calculate average score
        avg_score = (technical_score + communication_score + confidence_score) / 3

        # Adjust difficulty based on performance
        if avg_score < 0.4 and self.current_difficulty != DifficultyLevel.BEGINNER:
            # If struggling, go down one difficulty level
            if self.current_difficulty == DifficultyLevel.EXPERT:
                return DifficultyLevel.ADVANCED
            elif self.current_difficulty == DifficultyLevel.ADVANCED:
                return DifficultyLevel.INTERMEDIATE
            elif self.current_difficulty == DifficultyLevel.INTERMEDIATE:
                return DifficultyLevel.BEGINNER
        elif avg_score > 0.8 and self.current_difficulty != DifficultyLevel.EXPERT:
            # If doing well, go up one difficulty level
            if self.current_difficulty == DifficultyLevel.BEGINNER:
                return DifficultyLevel.INTERMEDIATE
            elif self.current_difficulty == DifficultyLevel.INTERMEDIATE:
                return DifficultyLevel.ADVANCED
            elif self.current_difficulty == DifficultyLevel.ADVANCED:
                return DifficultyLevel.EXPERT

        # Otherwise, keep current difficulty
        return self.current_difficulty

    def _get_default_questions(self) -> List[Question]:
        """Fallback default questions"""
        return [
            Question(
                id="tech_1",
                text="Could you tell me about your experience with relevant technologies for this position?",
                type=QuestionType.TECHNICAL,
                difficulty=DifficultyLevel.BEGINNER,
                category="Technical Knowledge",
                expected_keywords=["experience", "technology", "skills", "project"],
            ),
            Question(
                id="behav_1",
                text="Describe a challenging situation you faced at work and how you handled it.",
                type=QuestionType.BEHAVIORAL,
                difficulty=DifficultyLevel.INTERMEDIATE,
                category="Problem Solving",
                expected_keywords=["challenge", "solution", "result", "teamwork"],
            ),
        ]

    def _get_fallback_question(self, difficulty: DifficultyLevel) -> Question:
        """Get a fallback question when generation fails"""
        difficulty_questions = {
            DifficultyLevel.BEGINNER: "Could you tell me about your background and experience?",
            DifficultyLevel.INTERMEDIATE: "Can you describe a project you're particularly proud of?",
            DifficultyLevel.ADVANCED: "How would you approach solving a complex technical problem?",
            DifficultyLevel.EXPERT: "Can you discuss your experience with system architecture and design patterns?",
        }

        difficulty_categories = {
            DifficultyLevel.BEGINNER: "Background",
            DifficultyLevel.INTERMEDIATE: "Experience",
            DifficultyLevel.ADVANCED: "Problem Solving",
            DifficultyLevel.EXPERT: "Architecture",
        }

        difficulty_keywords = {
            DifficultyLevel.BEGINNER: [
                "background",
                "experience",
                "skills",
                "introduction",
            ],
            DifficultyLevel.INTERMEDIATE: [
                "project",
                "challenges",
                "solutions",
                "achievements",
            ],
            DifficultyLevel.ADVANCED: ["approach", "problem", "solution", "technical"],
            DifficultyLevel.EXPERT: ["architecture", "design", "patterns", "systems"],
        }

        return Question(
            id=f"fallback_{difficulty.value}",
            text=difficulty_questions.get(difficulty, "Tell me about your experience."),
            type=QuestionType.BEHAVIORAL,
            difficulty=difficulty,
            category=difficulty_categories.get(difficulty, "Experience"),
            expected_keywords=difficulty_keywords.get(
                difficulty, ["experience", "skills"]
            ),
        )
