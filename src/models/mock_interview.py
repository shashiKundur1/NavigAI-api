from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid


class EmotionType(str, Enum):
    CONFIDENT = "confident"
    NERVOUS = "nervous"
    NEUTRAL = "neutral"
    ENTHUSIASTIC = "enthusiastic"
    UNCERTAIN = "uncertain"


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    PROBLEM_SOLVING = "problem-solving"
    CULTURAL_FIT = "cultural_fit"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class InterviewStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AudioAnalysis(BaseModel):
    pitch: Optional[float] = None
    speech_rate: Optional[float] = None
    pauses_count: Optional[int] = None
    fluency_score: float = 0.5
    emotion_scores: Dict[str, float] = {}
    clarity_score: float = 0.5
    pace_score: float = 0.5

    class Config:
        extra = "allow"


class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    type: QuestionType
    difficulty: DifficultyLevel
    category: str
    expected_keywords: List[str] = []


class Answer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_id: str
    text: str
    audio_duration: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    transcribed_text: str = ""
    emotion_scores: Dict[str, float] = {}
    sentiment_score: float = 0.0
    confidence_score: float = 0.5
    fluency_score: float = 0.5
    technical_score: float = 0.5


class PerformanceMetrics(BaseModel):
    communication_score: float = 0.0
    technical_score: float = 0.0
    emotional_intelligence_score: float = 0.0
    behavioral_score: float = 0.0
    overall_score: float = 0.0
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []


class ThompsonSamplingParams(BaseModel):
    question_type_success: Dict[QuestionType, int] = {}
    question_type_failure: Dict[QuestionType, int] = {}
    difficulty_success: Dict[DifficultyLevel, int] = {}
    difficulty_failure: Dict[DifficultyLevel, int] = {}


class InterviewSession(BaseModel):
    id: str = Field(
        default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    job_title: str
    job_description: str
    candidate_id: str
    status: InterviewStatus = InterviewStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    questions_asked: List[str] = []
    current_question_index: int = 0
    answers: List[Answer] = []
    adaptive_params: Dict[str, Any] = {}
    performance_metrics: Dict[str, Any] = {}
    thompson_params: ThompsonSamplingParams = ThompsonSamplingParams()


class InterviewReport(BaseModel):
    session_id: str
    candidate_id: str
    job_title: str
    generated_at: datetime = Field(default_factory=datetime.now)
    performance_metrics: PerformanceMetrics
    detailed_analysis: Dict[str, Any] = {}
    question_responses: List[Dict[str, Any]] = []
    improvement_suggestions: List[str] = []
