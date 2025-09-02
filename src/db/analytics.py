from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
from .firebase_init import get_db

logger = logging.getLogger(__name__)


def get_analytics_data(days: int = 30) -> Dict[str, Any]:
    """Get analytics data for the specified time period"""
    try:
        db = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get sessions in date range
        sessions = []
        docs = (
            db.collection("interview_sessions")
            .where("created_at", ">=", start_date)
            .stream()
        )
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        # Calculate analytics
        total_sessions = len(sessions)
        completed_sessions = len(
            [s for s in sessions if s.get("status") == "completed"]
        )

        # Calculate average scores
        technical_scores = []
        communication_scores = []
        for session in sessions:
            if session.get("performance_metrics"):
                metrics = session["performance_metrics"]
                technical_scores.append(metrics.get("technical_score", 0))
                communication_scores.append(metrics.get("communication_score", 0))

        avg_technical = (
            sum(technical_scores) / len(technical_scores) if technical_scores else 0
        )
        avg_communication = (
            sum(communication_scores) / len(communication_scores)
            if communication_scores
            else 0
        )

        analytics_data = {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (
                (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
            ),
            "average_technical_score": avg_technical,
            "average_communication_score": avg_communication,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }
        print(f"Analytics data retrieved for {days} days")
        return analytics_data
    except Exception as e:
        logger.error(f"Failed to get analytics data: {e}")
        return {}


def get_performance_trends(candidate_id: str, days: int = 90) -> Dict[str, Any]:
    """Get performance trends for a specific candidate"""
    try:
        from .user_management import get_user_sessions

        db = get_db()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get sessions for the candidate in date range
        sessions = []
        docs = (
            db.collection("interview_sessions")
            .where("candidate_id", "==", candidate_id)
            .where("created_at", ">=", start_date)
            .stream()
        )

        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        # Extract performance data
        performance_data = []
        for session in sessions:
            if session.get("performance_metrics") and session.get("created_at"):
                metrics = session["performance_metrics"]
                performance_data.append(
                    {
                        "date": session["created_at"].isoformat(),
                        "technical_score": metrics.get("technical_score", 0),
                        "communication_score": metrics.get("communication_score", 0),
                        "overall_score": metrics.get("overall_score", 0),
                    }
                )

        # Sort by date
        performance_data.sort(key=lambda x: x["date"])

        return {
            "candidate_id": candidate_id,
            "days": days,
            "performance_data": performance_data,
            "total_sessions": len(sessions),
        }
    except Exception as e:
        logger.error(f"Failed to get performance trends: {e}")
        return {}


def get_job_analytics(job_title: str, days: int = 30) -> Dict[str, Any]:
    """Get analytics data for a specific job title"""
    try:
        db = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get sessions for the job title in date range
        sessions = []
        docs = (
            db.collection("interview_sessions")
            .where("job_title", "==", job_title)
            .where("created_at", ">=", start_date)
            .stream()
        )

        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        # Calculate analytics
        total_sessions = len(sessions)
        completed_sessions = len(
            [s for s in sessions if s.get("status") == "completed"]
        )

        # Calculate average scores
        technical_scores = []
        communication_scores = []
        for session in sessions:
            if session.get("performance_metrics"):
                metrics = session["performance_metrics"]
                technical_scores.append(metrics.get("technical_score", 0))
                communication_scores.append(metrics.get("communication_score", 0))

        avg_technical = (
            sum(technical_scores) / len(technical_scores) if technical_scores else 0
        )
        avg_communication = (
            sum(communication_scores) / len(communication_scores)
            if communication_scores
            else 0
        )

        analytics_data = {
            "job_title": job_title,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (
                (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
            ),
            "average_technical_score": avg_technical,
            "average_communication_score": avg_communication,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }
        print(f"Job analytics data retrieved for {job_title}")
        return analytics_data
    except Exception as e:
        logger.error(f"Failed to get job analytics: {e}")
        return {}
