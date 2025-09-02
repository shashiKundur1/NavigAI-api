from typing import List, Dict, Any
import logging
from .firebase_init import get_db

logger = logging.getLogger(__name__)


def get_user_sessions(candidate_id: str) -> List[Dict[str, Any]]:
    """Get all sessions for a specific candidate"""
    try:
        db = get_db()
        sessions = []
        docs = (
            db.collection("interview_sessions")
            .where("candidate_id", "==", candidate_id)
            .stream()
        )
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)
        print(f"Retrieved {len(sessions)} sessions for candidate: {candidate_id}")
        return sessions
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        return []


def get_user_reports(candidate_id: str) -> List[Dict[str, Any]]:
    """Get all reports for a specific candidate"""
    try:
        db = get_db()
        reports = []
        # First get all sessions for the candidate
        session_ids = [s["id"] for s in get_user_sessions(candidate_id)]

        # Then get all reports for those sessions
        for session_id in session_ids:
            from .interview_reports import get_interview_report

            report = get_interview_report(session_id)
            if report:
                reports.append(report)

        print(f"Retrieved {len(reports)} reports for candidate: {candidate_id}")
        return reports
    except Exception as e:
        logger.error(f"Failed to get user reports: {e}")
        return []


def create_user_profile(candidate_id: str, user_data: Dict[str, Any]) -> bool:
    """Create or update user profile"""
    try:
        db = get_db()
        from datetime import datetime

        user_data["created_at"] = datetime.now()
        user_data["updated_at"] = datetime.now()

        doc_ref = db.collection("user_profiles").document(candidate_id)
        doc_ref.set(user_data, merge=True)
        print(f"User profile saved for candidate: {candidate_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create user profile: {e}")
        return False


def get_user_profile(candidate_id: str) -> Dict[str, Any]:
    """Get user profile for a candidate"""
    try:
        db = get_db()
        doc_ref = db.collection("user_profiles").document(candidate_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"User profile not found: {candidate_id}")
            return {}
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        return {}
