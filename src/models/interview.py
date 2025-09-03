# src/navigai_api/models/interview.py
"""
Interview data models for the NavigAI system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid


class InterviewStatus(Enum):
    """Interview session status enumeration"""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class QuestionType(Enum):
    """Question type enumeration"""

    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SITUATIONAL = "situational"
    GENERAL = "general"
    FOLLOWUP = "followup"


class DifficultyLevel(Enum):
    """Question difficulty level"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class InterviewQuestion:
    """Individual interview question data model"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str = ""
    question_type: QuestionType = QuestionType.GENERAL
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    expected_duration: int = 300  # seconds
    keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CandidateResponse:
    """Candidate response to an interview question"""

    question_id: str = ""
    response_text: str = ""
    response_audio_url: Optional[str] = None
    response_duration: int = 0  # seconds
    confidence_score: float = 0.0
    keywords_mentioned: List[str] = field(default_factory=list)
    sentiment_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterviewFeedback:
    """Feedback for a specific response"""

    response_id: str = ""
    overall_score: float = 0.0
    communication_score: float = 0.0
    technical_score: float = 0.0
    content_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterviewSession:
    """Complete interview session data model"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    job_title: str = ""
    job_description: str = ""
    company_name: str = ""
    interview_type: str = "general"  # general, technical, behavioral
    status: InterviewStatus = InterviewStatus.CREATED

    # LiveKit session data
    livekit_room_name: str = ""
    livekit_participant_token: str = ""

    # Interview configuration
    estimated_duration: int = 1800  # 30 minutes default
    max_questions: int = 10
    difficulty_level: DifficultyLevel = DifficultyLevel.MEDIUM

    # Interview progress
    questions: List[InterviewQuestion] = field(default_factory=list)
    responses: List[CandidateResponse] = field(default_factory=list)
    feedback: List[InterviewFeedback] = field(default_factory=list)
    current_question_index: int = 0

    # Session metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration: int = 0  # seconds

    # AI conversation context
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    ai_personality: str = "professional"  # professional, casual, formal

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "job_title": self.job_title,
            "job_description": self.job_description,
            "company_name": self.company_name,
            "interview_type": self.interview_type,
            "status": self.status.value,
            "livekit_room_name": self.livekit_room_name,
            "livekit_participant_token": self.livekit_participant_token,
            "estimated_duration": self.estimated_duration,
            "max_questions": self.max_questions,
            "difficulty_level": self.difficulty_level.value,
            "current_question_index": self.current_question_index,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "actual_duration": self.actual_duration,
            "conversation_context": self.conversation_context,
            "ai_personality": self.ai_personality,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type.value,
                    "difficulty": q.difficulty.value,
                    "expected_duration": q.expected_duration,
                    "keywords": q.keywords,
                    "created_at": q.created_at.isoformat(),
                }
                for q in self.questions
            ],
            "responses": [
                {
                    "question_id": r.question_id,
                    "response_text": r.response_text,
                    "response_audio_url": r.response_audio_url,
                    "response_duration": r.response_duration,
                    "confidence_score": r.confidence_score,
                    "keywords_mentioned": r.keywords_mentioned,
                    "sentiment_score": r.sentiment_score,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.responses
            ],
            "feedback": [
                {
                    "response_id": f.response_id,
                    "overall_score": f.overall_score,
                    "communication_score": f.communication_score,
                    "technical_score": f.technical_score,
                    "content_score": f.content_score,
                    "suggestions": f.suggestions,
                    "strengths": f.strengths,
                    "areas_for_improvement": f.areas_for_improvement,
                    "generated_at": f.generated_at.isoformat(),
                }
                for f in self.feedback
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewSession":
        """Create InterviewSession from dictionary (Firebase data)"""
        session = cls()

        # Basic fields
        session.id = data.get("id", session.id)
        session.user_id = data.get("user_id", "")
        session.job_title = data.get("job_title", "")
        session.job_description = data.get("job_description", "")
        session.company_name = data.get("company_name", "")
        session.interview_type = data.get("interview_type", "general")
        session.status = InterviewStatus(data.get("status", "created"))

        # LiveKit fields
        session.livekit_room_name = data.get("livekit_room_name", "")
        session.livekit_participant_token = data.get("livekit_participant_token", "")

        # Configuration
        session.estimated_duration = data.get("estimated_duration", 1800)
        session.max_questions = data.get("max_questions", 10)
        session.difficulty_level = DifficultyLevel(
            data.get("difficulty_level", "medium")
        )
        session.current_question_index = data.get("current_question_index", 0)

        # Timing
        if data.get("started_at"):
            session.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            session.completed_at = datetime.fromisoformat(data["completed_at"])
        session.actual_duration = data.get("actual_duration", 0)

        # Context
        session.conversation_context = data.get("conversation_context", {})
        session.ai_personality = data.get("ai_personality", "professional")

        # Timestamps
        if data.get("created_at"):
            session.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            session.updated_at = datetime.fromisoformat(data["updated_at"])

        # Questions
        for q_data in data.get("questions", []):
            question = InterviewQuestion(
                id=q_data.get("id", str(uuid.uuid4())),
                question_text=q_data.get("question_text", ""),
                question_type=QuestionType(q_data.get("question_type", "general")),
                difficulty=DifficultyLevel(q_data.get("difficulty", "medium")),
                expected_duration=q_data.get("expected_duration", 300),
                keywords=q_data.get("keywords", []),
                created_at=(
                    datetime.fromisoformat(q_data["created_at"])
                    if q_data.get("created_at")
                    else datetime.utcnow()
                ),
            )
            session.questions.append(question)

        # Responses
        for r_data in data.get("responses", []):
            response = CandidateResponse(
                question_id=r_data.get("question_id", ""),
                response_text=r_data.get("response_text", ""),
                response_audio_url=r_data.get("response_audio_url"),
                response_duration=r_data.get("response_duration", 0),
                confidence_score=r_data.get("confidence_score", 0.0),
                keywords_mentioned=r_data.get("keywords_mentioned", []),
                sentiment_score=r_data.get("sentiment_score", 0.0),
                timestamp=(
                    datetime.fromisoformat(r_data["timestamp"])
                    if r_data.get("timestamp")
                    else datetime.utcnow()
                ),
            )
            session.responses.append(response)

        # Feedback
        for f_data in data.get("feedback", []):
            feedback = InterviewFeedback(
                response_id=f_data.get("response_id", ""),
                overall_score=f_data.get("overall_score", 0.0),
                communication_score=f_data.get("communication_score", 0.0),
                technical_score=f_data.get("technical_score", 0.0),
                content_score=f_data.get("content_score", 0.0),
                suggestions=f_data.get("suggestions", []),
                strengths=f_data.get("strengths", []),
                areas_for_improvement=f_data.get("areas_for_improvement", []),
                generated_at=(
                    datetime.fromisoformat(f_data["generated_at"])
                    if f_data.get("generated_at")
                    else datetime.utcnow()
                ),
            )
            session.feedback.append(feedback)

        return session


@dataclass
class InterviewReport:
    """Complete interview assessment report"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    interview_session_id: str = ""
    user_id: str = ""

    # Overall scores
    overall_score: float = 0.0
    communication_score: float = 0.0
    technical_score: float = 0.0
    behavioral_score: float = 0.0
    confidence_level: float = 0.0

    # Detailed analysis
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Question-wise breakdown
    question_scores: Dict[str, float] = field(default_factory=dict)

    # Performance metrics
    average_response_time: float = 0.0
    total_speaking_time: int = 0
    fluency_score: float = 0.0
    vocabulary_complexity: float = 0.0

    # Report metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    report_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "interview_session_id": self.interview_session_id,
            "user_id": self.user_id,
            "overall_score": self.overall_score,
            "communication_score": self.communication_score,
            "technical_score": self.technical_score,
            "behavioral_score": self.behavioral_score,
            "confidence_level": self.confidence_level,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "question_scores": self.question_scores,
            "average_response_time": self.average_response_time,
            "total_speaking_time": self.total_speaking_time,
            "fluency_score": self.fluency_score,
            "vocabulary_complexity": self.vocabulary_complexity,
            "generated_at": self.generated_at.isoformat(),
            "report_version": self.report_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewReport":
        """Create InterviewReport from dictionary"""
        report = cls()

        report.id = data.get("id", report.id)
        report.interview_session_id = data.get("interview_session_id", "")
        report.user_id = data.get("user_id", "")
        report.overall_score = data.get("overall_score", 0.0)
        report.communication_score = data.get("communication_score", 0.0)
        report.technical_score = data.get("technical_score", 0.0)
        report.behavioral_score = data.get("behavioral_score", 0.0)
        report.confidence_level = data.get("confidence_level", 0.0)
        report.strengths = data.get("strengths", [])
        report.weaknesses = data.get("weaknesses", [])
        report.recommendations = data.get("recommendations", [])
        report.question_scores = data.get("question_scores", {})
        report.average_response_time = data.get("average_response_time", 0.0)
        report.total_speaking_time = data.get("total_speaking_time", 0)
        report.fluency_score = data.get("fluency_score", 0.0)
        report.vocabulary_complexity = data.get("vocabulary_complexity", 0.0)
        report.report_version = data.get("report_version", "1.0")

        if data.get("generated_at"):
            report.generated_at = datetime.fromisoformat(data["generated_at"])

        return report
