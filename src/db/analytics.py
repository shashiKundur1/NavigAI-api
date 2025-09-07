import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from models.interview import InterviewStatus

logger = logging.getLogger(__name__)


async def get_analytics_data(user_id: str) -> Dict[str, Any]:
    try:
        from .interview_sessions import get_sessions_by_user
        from .interview_reports import get_reports_by_user

        sessions = await get_sessions_by_user(user_id, limit=100)
        reports = await get_reports_by_user(user_id, limit=100)

        total_sessions = len(sessions)
        completed_sessions = len(
            [s for s in sessions if s.status == InterviewStatus.COMPLETED]
        )
        completion_rate = (
            (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        )

        total_interview_time = sum(
            s.actual_duration
            for s in sessions
            if s.actual_duration and s.actual_duration > 0
        )
        avg_interview_duration = (
            (total_interview_time / completed_sessions) if completed_sessions > 0 else 0
        )

        analytics_data = {
            "user_id": user_id,
            "total_interviews": total_sessions,
            "completed_interviews": completed_sessions,
            "completion_rate": round(completion_rate, 2),
            "total_interview_time_minutes": round(total_interview_time / 60, 2),
            "average_interview_duration_minutes": round(avg_interview_duration / 60, 2),
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Generated analytics data for user {user_id}")
        return analytics_data
    except Exception as e:
        logger.error(f"Error getting analytics data for user {user_id}: {e}")
        raise
