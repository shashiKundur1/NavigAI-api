"""
Interview session database operations for NavigAI
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .firebase_init import get_db

logger = logging.getLogger(__name__)

COLLECTION_NAME = "interview_sessions"


def save_interview_session(session_data: Dict[str, Any]) -> bool:
    """Save interview session to Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection(COLLECTION_NAME).document(session_data["id"])

        # Convert datetime objects to ISO strings for Firestore
        session_copy = session_data.copy()
        for key, value in session_copy.items():
            if isinstance(value, datetime):
                session_copy[key] = value.isoformat()

        doc_ref.set(session_copy)
        logger.info(f"Saved interview session {session_data['id']}")
        return True
    except Exception as e:
        logger.error(f"Error saving interview session: {e}")
        return False


def get_interview_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get interview session from Firestore"""
    try:
        db = get_db()
        doc = db.collection(COLLECTION_NAME).document(session_id).get()

        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error getting interview session {session_id}: {e}")
        return None


def update_interview_session(session_data: Dict[str, Any]) -> bool:
    """Update interview session in Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection(COLLECTION_NAME).document(session_data["id"])

        # Convert datetime objects to ISO strings for Firestore
        session_copy = session_data.copy()
        for key, value in session_copy.items():
            if isinstance(value, datetime):
                session_copy[key] = value.isoformat()

        doc_ref.update(session_copy)
        logger.info(f"Updated interview session {session_data['id']}")
        return True
    except Exception as e:
        logger.error(f"Error updating interview session: {e}")
        return False


def get_all_interview_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Get all interview sessions from Firestore"""
    try:
        db = get_db()
        query = db.collection(COLLECTION_NAME).limit(limit)
        docs = query.stream()

        sessions = []
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        return sessions
    except Exception as e:
        logger.error(f"Error getting all interview sessions: {e}")
        return []


def delete_interview_session(session_id: str) -> bool:
    """Delete interview session from Firestore"""
    try:
        db = get_db()
        db.collection(COLLECTION_NAME).document(session_id).delete()
        logger.info(f"Deleted interview session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting interview session {session_id}: {e}")
        return False


def get_sessions_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all interview sessions for a specific user"""
    try:
        db = get_db()
        query = (
            db.collection(COLLECTION_NAME)
            .where("candidate_id", "==", user_id)
            .limit(limit)
        )
        docs = query.stream()

        sessions = []
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        return sessions
    except Exception as e:
        logger.error(f"Error getting sessions for user {user_id}: {e}")
        return []


def update_session_status(session_id: str, status: str) -> bool:
    """Update interview session status"""
    try:
        db = get_db()
        doc_ref = db.collection(COLLECTION_NAME).document(session_id)
        doc_ref.update({"status": status, "updated_at": datetime.now().isoformat()})
        logger.info(f"Updated session {session_id} status to {status}")
        return True
    except Exception as e:
        logger.error(f"Error updating session status: {e}")
        return False


def get_sessions_by_status(status: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all interview sessions with a specific status"""
    try:
        db = get_db()
        query = (
            db.collection(COLLECTION_NAME).where("status", "==", status).limit(limit)
        )
        docs = query.stream()

        sessions = []
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        return sessions
    except Exception as e:
        logger.error(f"Error getting sessions with status {status}: {e}")
        return []


def count_user_sessions(user_id: str) -> int:
    """Count the number of sessions for a user"""
    try:
        db = get_db()
        query = db.collection(COLLECTION_NAME).where("candidate_id", "==", user_id)
        docs = query.stream()
        return len(list(docs))
    except Exception as e:
        logger.error(f"Error counting sessions for user {user_id}: {e}")
        return 0


def search_sessions(search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search sessions by job title or company name"""
    try:
        db = get_db()
        # Firestore doesn't support full-text search, so we'll do a simple contains match
        query = db.collection(COLLECTION_NAME).limit(limit)
        docs = query.stream()

        sessions = []
        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id

            # Simple text search in job_title and job_description
            if (
                search_term.lower() in session_data.get("job_title", "").lower()
                or search_term.lower()
                in session_data.get("job_description", "").lower()
            ):
                sessions.append(session_data)

        return sessions
    except Exception as e:
        logger.error(f"Error searching sessions: {e}")
        return []
