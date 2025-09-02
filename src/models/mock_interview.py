from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    PROBLEM_SOLVING = "problem_solving"
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


class EmotionType(str, Enum):
    CONFIDENT = "confident"
    NERVOUS = "nervous"
    NEUTRAL = "neutral"
    ENTHUSIASTIC = "enthusiastic"
    UNCERTAIN = "uncertain"


class Question(BaseModel):
    id: str
    text: str
    type: QuestionType
    difficulty: DifficultyLevel
    category: str
    expected_keywords: List[str] = []
    follow_up_questions: List[str] = []
    success_count: int = 0
    failure_count: int = 0


class Answer(BaseModel):
    question_id: str
    text: str
    audio_duration: float
    timestamp: datetime
    transcribed_text: str
    emotion_scores: Dict[str, float] = {}
    sentiment_score: float = 0.0
    confidence_score: float = 0.0
    fluency_score: float = 0.0
    technical_score: float = 0.0


class InterviewSession(BaseModel):
    id: str
    job_title: str
    job_description: str
    candidate_id: str
    status: InterviewStatus = InterviewStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    questions_asked: List[str] = []
    answers: List[Answer] = []
    current_question_index: int = 0
    performance_metrics: Dict[str, float] = {}
    adaptive_params: Dict[str, Any] = {}


class PerformanceMetrics(BaseModel):
    communication_score: float = 0.0
    technical_score: float = 0.0
    emotional_intelligence_score: float = 0.0
    behavioral_score: float = 0.0
    overall_score: float = 0.0
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []


class InterviewReport(BaseModel):
    session_id: str
    candidate_id: str
    job_title: str
    generated_at: datetime = Field(default_factory=datetime.now)
    performance_metrics: PerformanceMetrics
    detailed_analysis: Dict[str, Any]
    question_responses: List[Dict[str, Any]]
    improvement_suggestions: List[str]


class ThompsonSamplingParams(BaseModel):
    question_type_success: Dict[QuestionType, int] = Field(default_factory=dict)
    question_type_failure: Dict[QuestionType, int] = Field(default_factory=dict)
    difficulty_success: Dict[DifficultyLevel, int] = Field(default_factory=dict)
    difficulty_failure: Dict[DifficultyLevel, int] = Field(default_factory=dict)
    exploration_rate: float = 0.3
    learning_rate: float = 0.1


class AudioAnalysis(BaseModel):
    pitch: float = 0.0
    tone: str = "neutral"
    speech_rate: float = 0.0
    pauses_count: int = 0
    clarity_score: float = 0.0
    volume_score: float = 0.0
