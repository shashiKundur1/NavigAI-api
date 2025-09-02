import asyncio
import threading
import queue
import numpy as np
import whisper
import sounddevice as sd
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Callable
import json
from scipy import stats
from scipy.io import wavfile
import torch
from google import genai
from google.genai import types
from models.mock_interview import (
    InterviewSession,
    Question,
    Answer,
    QuestionType,
    DifficultyLevel,
    InterviewStatus,
    PerformanceMetrics,
    InterviewReport,
    ThompsonSamplingParams,
    AudioAnalysis,
    EmotionType,
)
from db.firebase_db import (
    save_interview_session,
    get_interview_session,
    update_interview_session,
)
from core.settings import Settings

# Import our services
from services.audio_analysis_service import AudioAnalysisService
from services.tts_service import TTSService
from services.question_generation_service import QuestionGenerationService
from services.thompson_sampling_service import ThompsonSamplingService
from services.report_generation_service import ReportGenerationService
import logging

logger = logging.getLogger(__name__)


class MockInterviewService:
    def __init__(self):
        # Initialize AI models with optimizations
        logger.info("Loading Whisper model...")

        # Check if CUDA is available and set device accordingly
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        # Load the appropriate Whisper model based on device
        try:
            whisper_model = getattr(Settings, "WHISPER_MODEL", "base")
            if self.device == "cuda":
                self.whisper_model = whisper.load_model(whisper_model).to(self.device)
            else:
                # For CPU, explicitly use FP32 to avoid warnings
                self.whisper_model = whisper.load_model(whisper_model, device="cpu")
                self.whisper_model = self.whisper_model.float()  # Explicitly use FP32
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            # Fallback to base model on CPU
            self.whisper_model = whisper.load_model("base", device="cpu")
            self.whisper_model = self.whisper_model.float()

        logger.info("Whisper model loaded successfully")

        # Initialize Gemini client with API key from settings
        if not Settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in the environment variables.")
        self.gemini_client = genai.Client(api_key=Settings.GEMINI_API_KEY)

        # Initialize our services
        self.audio_analysis_service = AudioAnalysisService()
        self.tts_service = TTSService()
        self.question_generation_service = QuestionGenerationService(self.gemini_client)
        self.thompson_sampling_service = ThompsonSamplingService()
        self.report_generation_service = ReportGenerationService()

        # Audio recording setup
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.sample_rate = getattr(Settings, "SAMPLE_RATE", 16000)
        self.channels = 1
        self.dtype = "int16"

        # Question bank and conversation history
        self.question_bank = []
        self.conversation_history = []

        # Performance tracking
        self.performance_history = []

    def create_interview_session(
        self, job_title: str, job_description: str, candidate_id: str
    ) -> InterviewSession:
        """Create a new interview session"""
        session = InterviewSession(
            id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            job_title=job_title,
            job_description=job_description,
            candidate_id=candidate_id,
            status=InterviewStatus.CREATED,
        )

        # Parse job description to understand requirements
        self._parse_job_requirements(session)

        # Generate initial questions from job description
        self.question_bank = (
            self.question_generation_service.generate_questions_from_job_description(
                job_title, job_description
            )
        )

        # Initialize Thompson Sampling parameters
        self.thompson_sampling_service.initialize_thompson_sampling(
            session, session.adaptive_params
        )

        # Save to Firebase
        save_interview_session(session.dict())

        return session

    def _parse_job_requirements(self, session: InterviewSession):
        """Parse job description to extract key requirements and skills"""
        prompt = f"""
        Analyze this job description and extract key requirements, skills, and qualifications:
        
        Job Title: {session.job_title}
        Job Description: {session.job_description}
        
        Provide a JSON response with:
        1. key_skills: list of technical skills required
        2. experience_level: beginner/intermediate/advanced/expert
        3. key_responsibilities: list of main responsibilities
        4. preferred_qualifications: list of preferred qualifications
        """

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )

            # Clean response text
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            requirements = json.loads(response_text)
            session.adaptive_params.update(requirements)
        except Exception as e:
            logger.error(f"Error parsing job requirements: {e}")
            # Fallback to basic parsing
            session.adaptive_params = {
                "key_skills": ["programming", "problem-solving"],
                "experience_level": "intermediate",
                "key_responsibilities": ["development", "testing"],
                "preferred_qualifications": ["communication", "teamwork"],
            }

    def start_interview(self, session_id: str) -> bool:
        """Start the interview session"""
        session_data = get_interview_session(session_id)
        if not session_data:
            return False

        session = InterviewSession(**session_data)
        session.status = InterviewStatus.IN_PROGRESS
        session.started_at = datetime.now()

        # Save updated session
        update_interview_session(session_id, session.dict())

        return True

    def get_next_question(self, session: InterviewSession) -> Optional[Question]:
        """Get the next question using advanced NLP and context awareness"""
        # Get candidate's current performance
        candidate_performance = self._get_current_performance(session)

        # Generate contextual next question
        next_question = (
            self.question_generation_service.generate_contextual_next_question(
                job_description=session.job_description,
                conversation_history=self.conversation_history,
                asked_questions=session.questions_asked,
                candidate_performance=candidate_performance,
            )
        )

        if next_question:
            # Add to asked questions
            session.questions_asked.append(next_question.id)
            session.current_question_index += 1

            # Save updated session
            update_interview_session(session.id, session.dict())

            return next_question

        return None

    def _get_current_performance(self, session: InterviewSession) -> Dict[str, float]:
        """Get current performance metrics for the candidate"""
        if not session.answers:
            return {
                "technical_score": 0.5,
                "communication_score": 0.5,
                "confidence_score": 0.5,
            }

        latest_answer = session.answers[-1]
        return {
            "technical_score": latest_answer.technical_score,
            "communication_score": (
                latest_answer.fluency_score + latest_answer.confidence_score
            )
            / 2,
            "confidence_score": latest_answer.confidence_score,
        }

    def start_audio_recording(self, session_id: str):
        """Start recording audio for the interview"""
        self.is_recording = True
        self.audio_queue = queue.Queue()

        # Start recording thread
        recording_thread = threading.Thread(
            target=self._record_audio, args=(session_id,)
        )
        recording_thread.daemon = True
        recording_thread.start()

    def _record_audio(self, session_id: str):
        """Record audio in a separate thread"""

        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            if self.is_recording:
                self.audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                callback=audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
            ):
                while self.is_recording:
                    sd.sleep(100)  # Sleep for 100ms
        except Exception as e:
            logger.error(f"Audio recording error: {e}")

    def stop_audio_recording(self) -> Optional[str]:
        """Stop recording and return the audio file path"""
        self.is_recording = False

        # Collect all audio data
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())

        if not audio_data:
            return None

        # Concatenate and save audio
        audio_array = np.concatenate(audio_data, axis=0)

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wavfile.write(temp_file.name, self.sample_rate, audio_array)

        return temp_file.name

    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio using Whisper with optimizations"""
        try:
            # Use optimized settings for transcription
            options = {
                "fp16": (
                    False if self.device == "cpu" else True
                ),  # Only use FP16 on CUDA
                "language": "en",  # Set language to improve accuracy
                "task": "transcribe",
                "temperature": 0.0,  # Lower temperature for more consistent results
            }

            result = self.whisper_model.transcribe(audio_file_path, **options)
            return result["text"]
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def analyze_response(
        self,
        audio_file_path: str,
        transcribed_text: str,
        question: Question,
        session: InterviewSession,
    ) -> Answer:
        """Analyze the candidate's response using multi-modal analysis"""
        # Audio analysis using our optimized service
        audio_analysis = self.audio_analysis_service.analyze_audio_features(
            audio_file_path
        )

        # Text analysis using Gemini
        text_analysis = self._analyze_text_response(transcribed_text, question)

        # Create answer object
        answer = Answer(
            question_id=question.id,
            text=transcribed_text,
            audio_duration=self.audio_analysis_service.get_audio_duration(
                audio_file_path
            ),
            timestamp=datetime.now(),
            transcribed_text=transcribed_text,
            emotion_scores=audio_analysis.emotion_scores,
            sentiment_score=text_analysis["sentiment_score"],
            confidence_score=text_analysis["confidence_score"],
            fluency_score=audio_analysis.fluency_score,
            technical_score=text_analysis["technical_score"],
        )

        return answer

    def _analyze_text_response(self, text: str, question: Question) -> Dict[str, float]:
        """Analyze text response using Gemini"""
        prompt = f"""
        Analyze this interview response and provide scores for different aspects:
        
        Question: {question.text}
        Response: {text}
        Expected Keywords: {', '.join(question.expected_keywords)}
        
        Provide a JSON response with:
        1. technical_score: 0-1 score for technical accuracy
        2. sentiment_score: -1 to 1 (-1 negative, 0 neutral, 1 positive)
        3. confidence_score: 0-1 score for confidence level
        4. relevance_score: 0-1 score for relevance to question
        5. clarity_score: 0-1 score for clarity and structure
        """

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )

            # Clean response text
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            analysis = json.loads(response_text)
            return analysis

        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            return {
                "technical_score": 0.5,
                "sentiment_score": 0.0,
                "confidence_score": 0.5,
                "relevance_score": 0.5,
                "clarity_score": 0.5,
            }

    def submit_answer(self, session_id: str, answer: Answer):
        """Submit an answer and update session"""
        session_data = get_interview_session(session_id)
        if not session_data:
            return

        session = InterviewSession(**session_data)
        session.answers.append(answer)

        # Add to conversation history
        question_text = ""
        for q in self.question_bank:
            if q.id == answer.question_id:
                question_text = q.text
                break

        self.conversation_history.append(
            {
                "question": question_text,
                "answer": answer.text,
                "timestamp": answer.timestamp,
            }
        )

        # Update Thompson sampling parameters
        question = next(
            (q for q in self.question_bank if q.id == answer.question_id), None
        )
        if question:
            self.thompson_sampling_service.update_thompson_params(answer, question)

        # Save updated session
        update_interview_session(session_id, session.dict())

    def should_end_interview(self, session_id: str) -> bool:
        """Determine if interview should be ended"""
        session_data = get_interview_session(session_id)
        if not session_data:
            return True

        session = InterviewSession(**session_data)

        # Check if maximum questions reached
        max_questions = getattr(Settings, "MAX_QUESTIONS", 20)
        if len(session.answers) >= max_questions:
            return True

        # Check if performance plateau detected
        if len(session.answers) >= 5:
            recent_scores = [answer.technical_score for answer in session.answers[-5:]]
            if np.std(recent_scores) < 0.1:  # Low variance indicates plateau
                return True

        # Check if consistently poor performance
        if len(session.answers) >= 3:
            recent_scores = [answer.technical_score for answer in session.answers[-3:]]
            if np.mean(recent_scores) < 0.4:  # Consistently poor
                return True

        return False

    def end_interview(self, session_id: str) -> bool:
        """End the interview session"""
        session_data = get_interview_session(session_id)
        if not session_data:
            return False

        session = InterviewSession(**session_data)
        session.status = InterviewStatus.COMPLETED
        session.completed_at = datetime.now()

        # Calculate final performance metrics
        performance_metrics = self._calculate_performance_metrics(session)
        session.performance_metrics = performance_metrics.dict()

        # Save updated session
        update_interview_session(session_id, session.dict())

        return True

    def _calculate_performance_metrics(
        self, session: InterviewSession
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if not session.answers:
            return PerformanceMetrics()

        # Calculate individual scores
        technical_scores = [answer.technical_score for answer in session.answers]
        communication_scores = [
            (answer.fluency_score + answer.confidence_score) / 2
            for answer in session.answers
        ]
        emotional_scores = [
            max(answer.emotion_scores.values()) if answer.emotion_scores else 0.5
            for answer in session.answers
        ]
        behavioral_scores = [answer.sentiment_score for answer in session.answers]

        # Calculate overall scores
        metrics = PerformanceMetrics()
        metrics.communication_score = np.mean(communication_scores)
        metrics.technical_score = np.mean(technical_scores)
        metrics.emotional_intelligence_score = np.mean(emotional_scores)
        metrics.behavioral_score = np.mean(behavioral_scores)
        metrics.overall_score = np.mean(
            [np.mean(technical_scores), np.mean(communication_scores)]
        )

        # Identify strengths and weaknesses
        metrics.strengths = self._identify_strengths(metrics)
        metrics.weaknesses = self._identify_weaknesses(metrics)

        # Generate recommendations
        metrics.recommendations = self._generate_recommendations(metrics, session)

        return metrics

    def _identify_strengths(self, metrics: PerformanceMetrics) -> List[str]:
        """Identify candidate's strengths"""
        strengths = []

        if metrics.technical_score >= 0.8:
            strengths.append("Strong technical knowledge")
        if metrics.communication_score >= 0.8:
            strengths.append("Excellent communication skills")
        if metrics.emotional_intelligence_score >= 0.8:
            strengths.append("High emotional intelligence")
        if metrics.behavioral_score >= 0.8:
            strengths.append("Good behavioral responses")

        return strengths if strengths else ["Areas for improvement identified"]

    def _identify_weaknesses(self, metrics: PerformanceMetrics) -> List[str]:
        """Identify candidate's weaknesses"""
        weaknesses = []

        if metrics.technical_score < 0.6:
            weaknesses.append("Technical knowledge needs improvement")
        if metrics.communication_score < 0.6:
            weaknesses.append("Communication skills need development")
        if metrics.emotional_intelligence_score < 0.6:
            weaknesses.append("Emotional intelligence could be enhanced")
        if metrics.behavioral_score < 0.6:
            weaknesses.append("Behavioral responses need refinement")

        return weaknesses if weaknesses else ["No significant weaknesses identified"]

    def _generate_recommendations(
        self, metrics: PerformanceMetrics, session: InterviewSession
    ) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []

        # Technical recommendations
        if metrics.technical_score < 0.7:
            key_skills = session.adaptive_params.get("key_skills", [])
            if key_skills:
                recommendations.append(
                    f"Focus on improving {', '.join(key_skills[:2])} skills"
                )

        # Communication recommendations
        if metrics.communication_score < 0.7:
            recommendations.append("Practice clear and structured communication")

        # Confidence recommendations
        if metrics.emotional_intelligence_score < 0.7:
            recommendations.append("Work on confidence and stress management")

        # General recommendations
        recommendations.append("Continue practicing mock interviews")
        recommendations.append("Research the company and role thoroughly")

        return recommendations

    def generate_interview_report(self, session_id: str) -> Optional[str]:
        """Generate comprehensive PDF report"""
        session_data = get_interview_session(session_id)
        if not session_data:
            return None

        session = InterviewSession(**session_data)
        return self.report_generation_service.generate_interview_report(session)

    def text_to_speech(self, text: str, callback: Optional[Callable] = None) -> bool:
        """Convert text to speech with optional callback"""
        return self.tts_service.text_to_speech(text, blocking=False, callback=callback)
