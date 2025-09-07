import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from google.cloud.firestore import FieldFilter

from .firebase_init import get_collection, COLLECTIONS
from models.user import UserProfile

logger = logging.getLogger(__name__)


async def create_user_profile(profile: UserProfile) -> str:
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        profile_data = profile.to_dict()
        update_time, doc_ref = await asyncio.to_thread(collection.add, profile_data)
        logger.info(f"User profile created with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        raise


async def get_user_profile(user_id: str) -> Optional[UserProfile]:
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(user_id)
        doc = await asyncio.to_thread(doc_ref.get)
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = doc.id
        return UserProfile.from_dict(data)
    except Exception as e:
        logger.error(f"Error getting user profile {user_id}: {e}")
        raise


async def get_user_by_email(email: str) -> Optional[UserProfile]:
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        query = collection.where(filter=FieldFilter("email", "==", email)).limit(1)
        docs = await asyncio.to_thread(query.get)
        if not docs:
            return None
        doc = docs[0]
        data = doc.to_dict()
        data["id"] = doc.id
        return UserProfile.from_dict(data)
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        raise


async def update_user_profile(user_id: str, data: dict) -> bool:
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(user_id)
        if "password" in data:
            del data["password"]
        data["updated_at"] = datetime.utcnow()
        await asyncio.to_thread(doc_ref.update, data)
        logger.info(f"User profile {user_id} updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating user profile {user_id}: {e}")
        raise


async def get_user_sessions(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        from .interview_sessions import get_sessions_by_user

        sessions = await get_sessions_by_user(user_id, limit)
        return [session.to_dict() for session in sessions]
    except Exception as e:
        logger.error(f"Error getting user sessions {user_id}: {e}")
        raise


async def get_user_reports(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        from .interview_reports import get_reports_by_user

        reports = await get_reports_by_user(user_id, limit)
        return [report.to_dict() for report in reports]
    except Exception as e:
        logger.error(f"Error getting user reports {user_id}: {e}")
        raise
