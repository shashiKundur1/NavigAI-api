import logging
import asyncio
from .firebase_init import get_collection, COLLECTIONS
from google.cloud.firestore import FieldFilter

logger = logging.getLogger(__name__)


async def save_job_search(search_record: dict) -> str:
    try:
        collection = get_collection(COLLECTIONS["job_searches"])
        update_time, doc_ref = await asyncio.to_thread(collection.add, search_record)
        logger.info(f"Job search saved with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Error saving job search: {e}")
        raise


async def get_job_searches_by_user(user_id: str) -> list:
    try:
        collection = get_collection(COLLECTIONS["job_searches"])
        query = collection.where(filter=FieldFilter("user_id", "==", user_id))
        docs = await asyncio.to_thread(query.get)
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Error getting job searches for user {user_id}: {e}")
        return []
