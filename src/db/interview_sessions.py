import logging
import asyncio
from typing import Dict, Any, List, Optional
from google.cloud.firestore import FieldFilter

from .firebase_init import get_collection, COLLECTIONS
from models.interview import InterviewSession

logger = logging.getLogger(__name__)


async def save_interview_session(session: InterviewSession) -> str:
    try:
        collection = get_collection(COLLECTIONS["interview_sessions"])
        session_data = session.to_dict()
        update_time, doc_ref = await asyncio.to_thread(collection.add, session_data)
        logger.info(f"Saved interview session with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Error saving interview session: {e}")
        raise


async def get_interview_session(session_id: str) -> Optional[InterviewSession]:
    try:
        collection = get_collection(COLLECTIONS["interview_sessions"])
        doc_ref = collection.document(session_id)
        doc = await asyncio.to_thread(doc_ref.get)
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return InterviewSession.from_dict(data)
        return None
    except Exception as e:
        logger.error(f"Error getting interview session {session_id}: {e}")
        raise


async def update_interview_session(session_id: str, data: Dict[str, Any]) -> bool:
    try:
        collection = get_collection(COLLECTIONS["interview_sessions"])
        doc_ref = collection.document(session_id)
        await asyncio.to_thread(doc_ref.update, data)
        logger.info(f"Updated interview session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating interview session: {e}")
        raise


async def get_all_interview_sessions(limit: int = 50) -> List[InterviewSession]:
    try:
        collection = get_collection(COLLECTIONS["interview_sessions"])
        query = collection.limit(limit)
        docs = await asyncio.to_thread(query.get)
        sessions = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            sessions.append(InterviewSession.from_dict(data))
        return sessions
    except Exception as e:
        logger.error(f"Error getting all interview sessions: {e}")
        return []


async def get_sessions_by_user(user_id: str, limit: int = 50) -> List[InterviewSession]:
    try:
        collection = get_collection(COLLECTIONS["interview_sessions"])
        query = collection.where(filter=FieldFilter("user_id", "==", user_id)).limit(
            limit
        )
        docs = await asyncio.to_thread(query.get)
        sessions = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            sessions.append(InterviewSession.from_dict(data))
        return sessions
    except Exception as e:
        logger.error(f"Error getting sessions for user {user_id}: {e}")
        return []
