import logging
import asyncio
from .firebase_init import get_collection, COLLECTIONS

logger = logging.getLogger(__name__)


async def save_roadmap(user_id: str, roadmap_record: dict) -> None:
    try:
        collection = get_collection(COLLECTIONS["roadmaps"])
        doc_ref = collection.document(user_id)
        await asyncio.to_thread(doc_ref.set, roadmap_record, merge=True)
        logger.info(f"Roadmap saved for user ID: {user_id}")
    except Exception as e:
        logger.error(f"Error saving roadmap for user {user_id}: {e}")
        raise
