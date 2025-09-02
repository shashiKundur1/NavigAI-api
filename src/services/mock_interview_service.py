import asyncio
import threading
import queue
import numpy as np
import whisper
import pyttsx3
import sounddevice as sd
import scipy.io.wavfile as wav
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from google import genai
from google.genai import types
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile
import os
import json
import random
from scipy import stats
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
import db.firebase as firebase_db
from core.settings import Settings


class MockInterviewService:
    def __init__(self):
        # Initialize AI models
        self.whisper_model = whisper.load_model("turbo")

        # Initialize Gemini client with API key from settings
        if not Settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in the environment variables.")
        self.gemini_client = genai.Client(api_key=Settings.GEMINI_API_KEY)

        self.tts_engine = pyttsx3.init()

        # Configure TTS
        self.tts_engine.setProperty("rate", 150)
        self.tts_engine.setProperty("volume", 0.9)

        # Audio recording setup
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = "int16"

        # Question bank
        self.question_bank = self._initialize_question_bank()

        # Thompson sampling parameters
        self.thompson_params = ThompsonSamplingParams()

        # Performance tracking
        self.performance_history = []

    def _initialize_question_bank(self) -> List[Question]:
        """Initialize the question bank with various types of questions"""
        questions = [
            Question(
                id="tech_1",
                text="Explain the concept of object-oriented programming and its main principles.",
                type=QuestionType.TECHNICAL,
                difficulty=DifficultyLevel.INTERMEDIATE,
                category="Programming Fundamentals",
                expected_keywords=[
                    "encapsulation",
                    "inheritance",
                    "polymorphism",
                    "abstraction",
                ],
            ),
            Question(
                id="behav_1",
                text="Tell me about a time when you had to work with a difficult team member.",
                type=QuestionType.BEHAVIORAL,
                difficulty=DifficultyLevel.INTERMEDIATE,
                category="Teamwork",
                expected_keywords=[
                    "conflict",
                    "resolution",
                    "communication",
                    "collaboration",
                ],
            ),
            Question(
                id="sit_1",
                text="How would you handle a situation where you disagree with your manager's technical decision?",
                type=QuestionType.SITUATIONAL,
                difficulty=DifficultyLevel.ADVANCED,
                category="Problem Solving",
                expected_keywords=[
                    "respect",
                    "communication",
                    "evidence",
                    "compromise",
                ],
            ),
            Question(
                id="prob_1",
                text="Design a system for a URL shortening service like bit.ly.",
                type=QuestionType.PROBLEM_SOLVING,
                difficulty=DifficultyLevel.ADVANCED,
                category="System Design",
                expected_keywords=["database", "hashing", "scalability", "cache"],
            ),
            Question(
                id="cult_1",
                text="What type of work environment do you thrive in?",
                type=QuestionType.CULTURAL_FIT,
                difficulty=DifficultyLevel.BEGINNER,
                category="Culture",
                expected_keywords=[
                    "collaborative",
                    "independent",
                    "structured",
                    "flexible",
                ],
            ),
        ]
        return questions

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

        # Save to Firebase
        firebase_db.save_interview_session(session.dict())

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

        response = self.gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )

        try:
            requirements = json.loads(response.text)
            session.adaptive_params.update(requirements)
        except:
            # Fallback to basic parsing
            session.adaptive_params = {
                "key_skills": ["programming", "problem-solving"],
                "experience_level": "intermediate",
                "key_responsibilities": ["development", "testing"],
                "preferred_qualifications": ["communication", "teamwork"],
            }

    def start_interview(self, session_id: str) -> bool:
        """Start the interview session"""
        session_data = firebase_db.get_interview_session(session_id)
        if not session_data:
            return False

        session = InterviewSession(**session_data)
        session.status = InterviewStatus.IN_PROGRESS
        session.started_at = datetime.now()

        # Save updated session
        firebase_db.update_interview_session(session_id, session.dict())

        return True

    def thompson_sampling_question_selection(
        self, session: InterviewSession
    ) -> Question:
        """Select next question using Thompson Sampling"""
        # Sample from beta distributions for each question type
        type_samples = {}
        for q_type in QuestionType:
            alpha = self.thompson_params.question_type_success.get(q_type, 0) + 1
            beta = self.thompson_params.question_type_failure.get(q_type, 0) + 1
            type_samples[q_type] = np.random.beta(alpha, beta)

        # Sample from beta distributions for each difficulty level
        difficulty_samples = {}
        for diff in DifficultyLevel:
            alpha = self.thompson_params.difficulty_success.get(diff, 0) + 1
            beta = self.thompson_params.difficulty_failure.get(diff, 0) + 1
            difficulty_samples[diff] = np.random.beta(alpha, beta)

        # Get candidate's performance level
        performance_level = self._get_performance_level(session)

        # Filter questions based on job requirements and performance
        suitable_questions = []
        for question in self.question_bank:
            if question.id not in session.questions_asked:
                # Calculate suitability score
                type_score = type_samples.get(question.type, 0.5)
                difficulty_score = difficulty_samples.get(question.difficulty, 0.5)

                # Adjust difficulty based on performance
                if performance_level == "high" and question.difficulty in [
                    DifficultyLevel.BEGINNER,
                    DifficultyLevel.INTERMEDIATE,
                ]:
                    difficulty_score *= 0.7  # Reduce preference for easier questions
                elif performance_level == "low" and question.difficulty in [
                    DifficultyLevel.ADVANCED,
                    DifficultyLevel.EXPERT,
                ]:
                    difficulty_score *= 0.7  # Reduce preference for harder questions

                # Check if question matches job requirements
                relevance_score = self._calculate_question_relevance(question, session)

                total_score = (type_score + difficulty_score + relevance_score) / 3
                suitable_questions.append((question, total_score))

        # Select question with highest score
        if suitable_questions:
            suitable_questions.sort(key=lambda x: x[1], reverse=True)
            return suitable_questions[0][0]

        # Fallback to random question
        return random.choice(self.question_bank)

    def _get_performance_level(self, session: InterviewSession) -> str:
        """Get candidate's performance level based on answers"""
        if not session.answers:
            return "medium"

        avg_score = np.mean([answer.technical_score for answer in session.answers])

        if avg_score >= 0.8:
            return "high"
        elif avg_score >= 0.6:
            return "medium"
        else:
            return "low"

    def _calculate_question_relevance(
        self, question: Question, session: InterviewSession
    ) -> float:
        """Calculate how relevant a question is to the job requirements"""
        key_skills = session.adaptive_params.get("key_skills", [])
        experience_level = session.adaptive_params.get(
            "experience_level", "intermediate"
        )

        relevance = 0.5  # Base relevance

        # Check if question type matches job requirements
        if question.type == QuestionType.TECHNICAL and any(
            skill in question.text.lower() for skill in key_skills
        ):
            relevance += 0.3

        # Check difficulty match
        difficulty_mapping = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
            "expert": DifficultyLevel.EXPERT,
        }

        if question.difficulty == difficulty_mapping.get(
            experience_level, DifficultyLevel.INTERMEDIATE
        ):
            relevance += 0.2

        return min(relevance, 1.0)

    def get_next_question(self, session_id: str) -> Optional[Question]:
        """Get the next question for the interview"""
        session_data = firebase_db.get_interview_session(session_id)
        if not session_data:
            return None

        session = InterviewSession(**session_data)

        # Use Thompson Sampling to select next question
        question = self.thompson_sampling_question_selection(session)

        # Add to asked questions
        session.questions_asked.append(question.id)
        session.current_question_index += 1

        # Save updated session
        firebase_db.update_interview_session(session_id, session.dict())

        return question

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
                print(f"Audio callback status: {status}")
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
            print(f"Audio recording error: {e}")

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
        wav.write(temp_file.name, self.sample_rate, audio_array)

        return temp_file.name

    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio using Whisper"""
        try:
            result = self.whisper_model.transcribe(audio_file_path)
            return result["text"]
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def analyze_response(
        self,
        audio_file_path: str,
        transcribed_text: str,
        question: Question,
        session: InterviewSession,
    ) -> Answer:
        """Analyze the candidate's response using multi-modal analysis"""
        # Audio analysis
        audio_analysis = self._analyze_audio_features(audio_file_path)

        # Text analysis using Gemini
        text_analysis = self._analyze_text_response(transcribed_text, question)

        # Create answer object
        answer = Answer(
            question_id=question.id,
            text=transcribed_text,
            audio_duration=self._get_audio_duration(audio_file_path),
            timestamp=datetime.now(),
            transcribed_text=transcribed_text,
            emotion_scores=audio_analysis.emotion_scores,
            sentiment_score=text_analysis["sentiment_score"],
            confidence_score=text_analysis["confidence_score"],
            fluency_score=audio_analysis.fluency_score,
            technical_score=text_analysis["technical_score"],
        )

        return answer

    def _analyze_audio_features(self, audio_file_path: str) -> AudioAnalysis:
        """Analyze audio features for emotion and fluency"""
        try:
            sample_rate, audio_data = wav.read(audio_file_path)

            # Calculate basic audio features
            audio_analysis = AudioAnalysis()

            # Pitch analysis (simplified)
            pitches = []
            for i in range(0, len(audio_data) - 512, 256):
                frame = audio_data[i : i + 512]
                if len(frame) > 0:
                    # Simple pitch estimation using zero crossings
                    zero_crossings = np.sum(np.diff(np.sign(frame)) != 0)
                    pitch = zero_crossings * sample_rate / (2 * len(frame))
                    pitches.append(pitch)

            if pitches:
                audio_analysis.pitch = np.mean(pitches)

            # Speech rate estimation
            audio_analysis.speech_rate = (
                len(audio_data) / sample_rate
            )  # Duration in seconds

            # Pause detection (simplified)
            silence_threshold = 1000  # Adjust based on your audio
            silent_frames = np.sum(np.abs(audio_data) < silence_threshold)
            audio_analysis.pauses_count = silent_frames // (
                sample_rate // 10
            )  # Rough estimate

            # Fluency score (simplified)
            pause_ratio = audio_analysis.pauses_count / max(
                audio_analysis.speech_rate, 1
            )
            audio_analysis.fluency_score = max(0, 1 - pause_ratio)

            # Emotion scores (simplified - in real implementation, use ML models)
            audio_analysis.emotion_scores = {
                "confident": 0.7,
                "nervous": 0.2,
                "neutral": 0.1,
            }

            return audio_analysis

        except Exception as e:
            print(f"Audio analysis error: {e}")
            return AudioAnalysis()

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

            analysis = json.loads(response.text)
            return analysis

        except Exception as e:
            print(f"Text analysis error: {e}")
            return {
                "technical_score": 0.5,
                "sentiment_score": 0.0,
                "confidence_score": 0.5,
                "relevance_score": 0.5,
                "clarity_score": 0.5,
            }

    def _get_audio_duration(self, audio_file_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            sample_rate, audio_data = wav.read(audio_file_path)
            return len(audio_data) / sample_rate
        except:
            return 0.0

    def submit_answer(self, session_id: str, answer: Answer) -> bool:
        """Submit an answer and update session"""
        session_data = firebase_db.get_interview_session(session_id)
        if not session_data:
            return False

        session = InterviewSession(**session_data)
        session.answers.append(answer)

        # Update Thompson sampling parameters
        self._update_thompson_params(answer)

        # Save updated session
        firebase_db.update_interview_session(session_id, session.dict())

        return True

    def _update_thompson_params(self, answer: Answer):
        """Update Thompson sampling parameters based on answer performance"""
        # Get question
        question = next(
            (q for q in self.question_bank if q.id == answer.question_id), None
        )
        if not question:
            return

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

    def should_end_interview(self, session_id: str) -> bool:
        """Determine if interview should be ended based on performance and question count"""
        session_data = firebase_db.get_interview_session(session_id)
        if not session_data:
            return False

        session = InterviewSession(**session_data)

        # Check if maximum questions reached
        if len(session.answers) >= 10:  # Maximum 10 questions
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
        session_data = firebase_db.get_interview_session(session_id)
        if not session_data:
            return False

        session = InterviewSession(**session_data)
        session.status = InterviewStatus.COMPLETED
        session.completed_at = datetime.now()

        # Calculate final performance metrics
        performance_metrics = self._calculate_performance_metrics(session)
        session.performance_metrics = performance_metrics.dict()

        # Save updated session
        firebase_db.update_interview_session(session_id, session.dict())

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
            max(answer.emotion_scores.values()) for answer in session.answers
        ]
        behavioral_scores = [answer.sentiment_score for answer in session.answers]

        # Calculate overall scores
        metrics = PerformanceMetrics(
            communication_score=np.mean(communication_scores),
            technical_score=np.mean(technical_scores),
            emotional_intelligence_score=np.mean(emotional_scores),
            behavioral_score=np.mean(behavioral_scores),
            overall_score=np.mean(
                [np.mean(technical_scores), np.mean(communication_scores)]
            ),
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
        session_data = firebase_db.get_interview_session(session_id)
        if not session_data:
            return None

        session = InterviewSession(**session_data)
        performance_metrics = PerformanceMetrics(**session.performance_metrics)

        # Create report
        report = InterviewReport(
            session_id=session_id,
            candidate_id=session.candidate_id,
            job_title=session.job_title,
            performance_metrics=performance_metrics,
            detailed_analysis=self._generate_detailed_analysis(session),
            question_responses=self._generate_question_responses(session),
            improvement_suggestions=performance_metrics.recommendations,
        )

        # Generate PDF
        pdf_path = self._create_pdf_report(report)

        # Save report to Firebase
        firebase_db.save_interview_report(report.dict())

        return pdf_path

    def _generate_detailed_analysis(self, session: InterviewSession) -> Dict[str, Any]:
        """Generate detailed analysis of the interview"""
        analysis = {
            "total_questions": len(session.questions_asked),
            "total_answers": len(session.answers),
            "average_response_time": (
                np.mean([answer.audio_duration for answer in session.answers])
                if session.answers
                else 0
            ),
            "performance_trend": self._calculate_performance_trend(session),
            "question_type_breakdown": self._analyze_question_type_performance(session),
            "difficulty_progression": self._analyze_difficulty_progression(session),
        }
        return analysis

    def _calculate_performance_trend(self, session: InterviewSession) -> str:
        """Calculate performance trend over the interview"""
        if len(session.answers) < 3:
            return "Insufficient data"

        scores = [answer.technical_score for answer in session.answers]
        trend = stats.linregress(range(len(scores)), scores)

        if trend.slope > 0.05:
            return "Improving"
        elif trend.slope < -0.05:
            return "Declining"
        else:
            return "Stable"

    def _analyze_question_type_performance(
        self, session: InterviewSession
    ) -> Dict[str, float]:
        """Analyze performance by question type"""
        type_performance = {}

        for answer in session.answers:
            question = next(
                (q for q in self.question_bank if q.id == answer.question_id), None
            )
            if question:
                if question.type not in type_performance:
                    type_performance[question.type.value] = []
                type_performance[question.type.value].append(answer.technical_score)

        # Calculate averages
        return {q_type: np.mean(scores) for q_type, scores in type_performance.items()}

    def _analyze_difficulty_progression(
        self, session: InterviewSession
    ) -> Dict[str, Any]:
        """Analyze how difficulty progressed and performance changed"""
        difficulty_progression = []

        for answer in session.answers:
            question = next(
                (q for q in self.question_bank if q.id == answer.question_id), None
            )
            if question:
                difficulty_progression.append(
                    {
                        "question_index": len(difficulty_progression),
                        "difficulty": question.difficulty.value,
                        "score": answer.technical_score,
                    }
                )

        return {
            "progression": difficulty_progression,
            "difficulty_trend": self._calculate_difficulty_trend(
                difficulty_progression
            ),
        }

    def _calculate_difficulty_trend(self, progression: List[Dict[str, Any]]) -> str:
        """Calculate if difficulty increased appropriately"""
        if len(progression) < 3:
            return "Insufficient data"

        difficulty_mapping = {
            "beginner": 1,
            "intermediate": 2,
            "advanced": 3,
            "expert": 4,
        }

        difficulties = [difficulty_mapping[p["difficulty"]] for p in progression]
        trend = stats.linregress(range(len(difficulties)), difficulties)

        if trend.slope > 0.1:
            return "Increasing"
        elif trend.slope < -0.1:
            return "Decreasing"
        else:
            return "Stable"

    def _generate_question_responses(
        self, session: InterviewSession
    ) -> List[Dict[str, Any]]:
        """Generate detailed question-response analysis"""
        responses = []

        for answer in session.answers:
            question = next(
                (q for q in self.question_bank if q.id == answer.question_id), None
            )
            if question:
                response = {
                    "question": question.text,
                    "question_type": question.type.value,
                    "difficulty": question.difficulty.value,
                    "response": answer.text,
                    "score": answer.technical_score,
                    "feedback": self._generate_question_feedback(answer, question),
                }
                responses.append(response)

        return responses

    def _generate_question_feedback(self, answer: Answer, question: Question) -> str:
        """Generate feedback for a specific question"""
        if answer.technical_score >= 0.8:
            return "Excellent response! You demonstrated strong understanding."
        elif answer.technical_score >= 0.6:
            return "Good response with room for improvement."
        else:
            return "Consider reviewing this topic and practicing similar questions."

    def _create_pdf_report(self, report: InterviewReport) -> str:
        """Create PDF report using ReportLab"""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        pdf_path = temp_file.name
        temp_file.close()

        # Create PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
        )

        # Add title
        title = Paragraph("AI Mock Interview Report", title_style)
        story.append(title)

        # Add session info
        session_info = [
            ["Candidate ID", report.candidate_id],
            ["Job Title", report.job_title],
            ["Session ID", report.session_id],
            ["Generated", report.generated_at.strftime("%Y-%m-%d %H:%M:%S")],
        ]

        session_table = Table(session_info, colWidths=[2 * inch, 4 * inch])
        session_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(session_table)
        story.append(Spacer(1, 20))

        # Add performance metrics
        metrics = report.performance_metrics
        metrics_data = [
            ["Metric", "Score", "Assessment"],
            [
                "Technical Skills",
                f"{metrics.technical_score:.2f}",
                self._score_to_grade(metrics.technical_score),
            ],
            [
                "Communication",
                f"{metrics.communication_score:.2f}",
                self._score_to_grade(metrics.communication_score),
            ],
            [
                "Emotional Intelligence",
                f"{metrics.emotional_intelligence_score:.2f}",
                self._score_to_grade(metrics.emotional_intelligence_score),
            ],
            [
                "Behavioral",
                f"{metrics.behavioral_score:.2f}",
                self._score_to_grade(metrics.behavioral_score),
            ],
            [
                "Overall",
                f"{metrics.overall_score:.2f}",
                self._score_to_grade(metrics.overall_score),
            ],
        ]

        metrics_table = Table(metrics_data, colWidths=[2 * inch, 1 * inch, 2 * inch])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(Paragraph("Performance Metrics", styles["Heading2"]))
        story.append(metrics_table)
        story.append(Spacer(1, 20))

        # Add performance chart
        chart_path = self._create_performance_chart(metrics)
        if chart_path:
            story.append(Image(chart_path, width=6 * inch, height=3 * inch))
            story.append(Spacer(1, 20))

        # Add strengths and weaknesses
        story.append(Paragraph("Strengths", styles["Heading2"]))
        for strength in metrics.strengths:
            story.append(Paragraph(f"• {strength}", styles["Normal"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Areas for Improvement", styles["Heading2"]))
        for weakness in metrics.weaknesses:
            story.append(Paragraph(f"• {weakness}", styles["Normal"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Recommendations", styles["Heading2"]))
        for recommendation in metrics.recommendations:
            story.append(Paragraph(f"• {recommendation}", styles["Normal"]))

        # Build PDF
        doc.build(story)

        # Clean up chart file
        if chart_path and os.path.exists(chart_path):
            os.remove(chart_path)

        return pdf_path

    def _score_to_grade(self, score: float) -> str:
        """Convert score to grade"""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Very Good"
        elif score >= 0.7:
            return "Good"
        elif score >= 0.6:
            return "Fair"
        else:
            return "Needs Improvement"

    def _create_performance_chart(self, metrics: PerformanceMetrics) -> Optional[str]:
        """Create performance chart"""
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 4))

            # Data
            categories = [
                "Technical",
                "Communication",
                "Emotional\nIntelligence",
                "Behavioral",
                "Overall",
            ]
            scores = [
                metrics.technical_score,
                metrics.communication_score,
                metrics.emotional_intelligence_score,
                metrics.behavioral_score,
                metrics.overall_score,
            ]

            # Create bar chart
            bars = ax.bar(
                categories,
                scores,
                color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            )

            # Customize chart
            ax.set_ylim(0, 1)
            ax.set_ylabel("Score")
            ax.set_title("Performance Metrics")

            # Add value labels on bars
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 0.01,
                    f"{score:.2f}",
                    ha="center",
                    va="bottom",
                )

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            plt.tight_layout()
            plt.savefig(temp_file.name, dpi=150, bbox_inches="tight")
            plt.close()

            return temp_file.name

        except Exception as e:
            print(f"Chart creation error: {e}")
            return None

    def text_to_speech(self, text: str) -> bool:
        """Convert text to speech"""
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS error: {e}")
            return False
