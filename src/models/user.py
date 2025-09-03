# src/navigai_api/models/user.py
"""
User data models for the NavigAI system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid


class UserRole(Enum):
    """User role enumeration"""

    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class SubscriptionType(Enum):
    """Subscription type enumeration"""

    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class UserProfile:
    """User profile data model"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    full_name: str = ""
    role: UserRole = UserRole.CANDIDATE

    # Professional information
    current_job_title: str = ""
    experience_years: int = 0
    skills: List[str] = field(default_factory=list)
    target_roles: List[str] = field(default_factory=list)
    preferred_industries: List[str] = field(default_factory=list)

    # Subscription information
    subscription_type: SubscriptionType = SubscriptionType.FREE
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None

    # Interview preferences
    preferred_interview_duration: int = 1800  # 30 minutes
    preferred_difficulty: str = "medium"
    interview_goals: List[str] = field(default_factory=list)

    # Performance tracking
    total_interviews: int = 0
    average_score: float = 0.0
    improvement_areas: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "current_job_title": self.current_job_title,
            "experience_years": self.experience_years,
            "skills": self.skills,
            "target_roles": self.target_roles,
            "preferred_industries": self.preferred_industries,
            "subscription_type": self.subscription_type.value,
            "subscription_start": (
                self.subscription_start.isoformat() if self.subscription_start else None
            ),
            "subscription_end": (
                self.subscription_end.isoformat() if self.subscription_end else None
            ),
            "preferred_interview_duration": self.preferred_interview_duration,
            "preferred_difficulty": self.preferred_difficulty,
            "interview_goals": self.interview_goals,
            "total_interviews": self.total_interviews,
            "average_score": self.average_score,
            "improvement_areas": self.improvement_areas,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create UserProfile from dictionary (Firebase data)"""
        profile = cls()

        profile.id = data.get("id", profile.id)
        profile.email = data.get("email", "")
        profile.full_name = data.get("full_name", "")
        profile.role = UserRole(data.get("role", "candidate"))
        profile.current_job_title = data.get("current_job_title", "")
        profile.experience_years = data.get("experience_years", 0)
        profile.skills = data.get("skills", [])
        profile.target_roles = data.get("target_roles", [])
        profile.preferred_industries = data.get("preferred_industries", [])
        profile.subscription_type = SubscriptionType(
            data.get("subscription_type", "free")
        )

        # Parse datetime fields
        if data.get("subscription_start"):
            profile.subscription_start = datetime.fromisoformat(
                data["subscription_start"]
            )
        if data.get("subscription_end"):
            profile.subscription_end = datetime.fromisoformat(data["subscription_end"])

        profile.preferred_interview_duration = data.get(
            "preferred_interview_duration", 1800
        )
        profile.preferred_difficulty = data.get("preferred_difficulty", "medium")
        profile.interview_goals = data.get("interview_goals", [])
        profile.total_interviews = data.get("total_interviews", 0)
        profile.average_score = data.get("average_score", 0.0)
        profile.improvement_areas = data.get("improvement_areas", [])

        if data.get("created_at"):
            profile.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            profile.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_login"):
            profile.last_login = datetime.fromisoformat(data["last_login"])

        return profile
