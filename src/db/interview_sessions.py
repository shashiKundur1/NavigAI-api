from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .firebase_init import get_db

logger = logging.getLogger(__name__)


def save_interview_session(session_data: Dict[str, Any]) -> bool:
    """Save interview session to Firestore"""
    try:
        db = get_db()
        # Add timestamp
        session_data["created_at"] = datetime.now()
        session_data["updated_at"] = datetime.now()
        # Save to Firestore
        doc_ref = db.collection("interview_sessions").document(session_data["id"])
        doc_ref.set(session_data)
        print(f"Interview session saved: {session_data['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to save interview session: {e}")
        return False


def get_interview_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get interview session from Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection("interview_sessions").document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"Interview session not found: {session_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to get interview session: {e}")
        return None


def update_interview_session(session_id: str, session_data: Dict[str, Any]) -> bool:
    """Update interview session in Firestore"""
    try:
        db = get_db()
        # Add update timestamp
        session_data["updated_at"] = datetime.now()
        # Update in Firestore
        doc_ref = db.collection("interview_sessions").document(session_id)
        doc_ref.update(session_data)
        print(f"Interview session updated: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update interview session: {e}")
        return False


def get_all_interview_sessions() -> List[Dict[str, Any]]:
    """Get all interview sessions from Firestore"""
    try:
        db = get_db()
        sessions = []
        docs = db.collection("interview_sessions").stream()
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)
        print(f"Retrieved {len(sessions)} interview sessions")
        return sessions
    except Exception as e:
        logger.error(f"Failed to get interview sessions: {e}")
        return []


def delete_interview_session(session_id: str) -> bool:
    """Delete interview session and related data"""
    try:
        db = get_db()
        # Delete session
        doc_ref = db.collection("interview_sessions").document(session_id)
        doc_ref.delete()

        # Delete related report if exists
        from .interview_reports import delete_interview_report

        delete_interview_report(session_id)

        print(f"Interview session deleted: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete interview session: {e}")
        return False
