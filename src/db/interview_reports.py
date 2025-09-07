import logging
import asyncio
from typing import List, Optional
from google.cloud.firestore import FieldFilter, Query

from .firebase_init import get_collection, COLLECTIONS
from models.interview import InterviewReport

logger = logging.getLogger(__name__)


async def save_interview_report(report: InterviewReport) -> str:
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        report_data = report.to_dict()
        update_time, doc_ref = await asyncio.to_thread(collection.add, report_data)
        logger.info(f"Interview report saved with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Error saving interview report: {e}")
        raise


async def get_interview_report(report_id: str) -> Optional[InterviewReport]:
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        doc_ref = collection.document(report_id)
        doc = await asyncio.to_thread(doc_ref.get)
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = doc.id
        return InterviewReport.from_dict(data)
    except Exception as e:
        logger.error(f"Error getting interview report {report_id}: {e}")
        raise


async def get_reports_by_user(user_id: str, limit: int = 50) -> List[InterviewReport]:
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        query = (
            collection.where(filter=FieldFilter("user_id", "==", user_id))
            .order_by("generated_at", direction=Query.DESCENDING)
            .limit(limit)
        )
        docs = await asyncio.to_thread(query.get)
        reports = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            reports.append(InterviewReport.from_dict(data))
        return reports
    except Exception as e:
        logger.error(f"Error getting reports for user {user_id}: {e}")
        raise
