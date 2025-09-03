# src/firebase_db/interview_reports.py
"""
Firebase operations for interview reports in NavigAI
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.cloud.firestore import FieldFilter, Query
from google.cloud import firestore

from .firebase_init import (
    get_db,
    get_collection,
    COLLECTIONS,
    DocumentNotFoundError,
    ValidationError,
)
from ..models.interview import InterviewReport

logger = logging.getLogger(__name__)


async def save_interview_report(report: InterviewReport) -> str:
    """
    Save interview report to Firestore

    Args:
        report (InterviewReport): Interview report to save

    Returns:
        str: Document ID of saved report
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])

        # Convert report to dictionary
        report_data = report.model_dump()
        report_data["generated_at"] = firestore.SERVER_TIMESTAMP

        # Save to Firestore
        doc_ref = await collection.add(report_data)

        logger.info(f"Interview report saved with ID: {doc_ref[1].id}")
        return doc_ref[1].id

    except Exception as e:
        logger.error(f"Error saving interview report: {e}")
        raise


async def get_interview_report(report_id: str) -> Optional[InterviewReport]:
    """
    Get interview report by ID

    Args:
        report_id (str): Report ID to retrieve

    Returns:
        Optional[InterviewReport]: Interview report if found
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        doc_ref = collection.document(report_id)
        doc = await doc_ref.get()

        if not doc.exists:
            logger.warning(f"Interview report {report_id} not found")
            return None

        # Convert Firestore data to InterviewReport
        data = doc.to_dict()
        data["id"] = doc.id

        # Convert timestamps
        if data.get("generated_at"):
            data["generated_at"] = data["generated_at"].replace(tzinfo=None)

        return InterviewReport(**data)

    except Exception as e:
        logger.error(f"Error getting interview report {report_id}: {e}")
        raise


async def get_report_by_session_id(session_id: str) -> Optional[InterviewReport]:
    """
    Get interview report by session ID

    Args:
        session_id (str): Interview session ID

    Returns:
        Optional[InterviewReport]: Interview report if found
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        query = collection.where(
            filter=FieldFilter("interview_session_id", "==", session_id)
        ).limit(1)

        docs = await query.get()

        if not docs:
            logger.warning(f"No report found for session {session_id}")
            return None

        doc = docs[0]
        data = doc.to_dict()
        data["id"] = doc.id

        # Convert timestamps
        if data.get("generated_at"):
            data["generated_at"] = data["generated_at"].replace(tzinfo=None)

        return InterviewReport(**data)

    except Exception as e:
        logger.error(f"Error getting report for session {session_id}: {e}")
        raise


async def get_all_interview_reports(
    limit: int = 100,
    offset: int = 0,
    user_id_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[InterviewReport]:
    """
    Get all interview reports with optional filtering

    Args:
        limit (int): Maximum number of reports to return
        offset (int): Number of reports to skip
        user_id_filter (Optional[str]): Filter by user ID
        start_date (Optional[datetime]): Filter reports after this date
        end_date (Optional[datetime]): Filter reports before this date

    Returns:
        List[InterviewReport]: List of interview reports
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        query = collection.order_by("generated_at", direction=Query.DESCENDING)

        # Apply filters
        if user_id_filter:
            query = query.where(filter=FieldFilter("user_id", "==", user_id_filter))

        if start_date:
            query = query.where(filter=FieldFilter("generated_at", ">=", start_date))

        if end_date:
            query = query.where(filter=FieldFilter("generated_at", "<=", end_date))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        docs = await query.get()

        reports = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Convert timestamps
            if data.get("generated_at"):
                data["generated_at"] = data["generated_at"].replace(tzinfo=None)

            reports.append(InterviewReport(**data))

        logger.info(f"Retrieved {len(reports)} interview reports")
        return reports

    except Exception as e:
        logger.error(f"Error getting interview reports: {e}")
        raise


async def delete_interview_report(report_id: str) -> bool:
    """
    Delete interview report from Firestore

    Args:
        report_id (str): Report ID to delete

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        doc_ref = collection.document(report_id)

        # Check if document exists
        doc = await doc_ref.get()
        if not doc.exists:
            logger.warning(f"Interview report {report_id} not found for deletion")
            return False

        await doc_ref.delete()

        logger.info(f"Interview report {report_id} deleted successfully")
        return True

    except Exception as e:
        logger.error(f"Error deleting interview report {report_id}: {e}")
        raise


async def get_reports_by_user(user_id: str, limit: int = 50) -> List[InterviewReport]:
    """
    Get all interview reports for a specific user

    Args:
        user_id (str): User ID to filter by
        limit (int): Maximum number of reports to return

    Returns:
        List[InterviewReport]: List of user's interview reports
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        query = (
            collection.where(filter=FieldFilter("user_id", "==", user_id))
            .order_by("generated_at", direction=Query.DESCENDING)
            .limit(limit)
        )

        docs = await query.get()

        reports = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Convert timestamps
            if data.get("generated_at"):
                data["generated_at"] = data["generated_at"].replace(tzinfo=None)

            reports.append(InterviewReport(**data))

        logger.info(f"Retrieved {len(reports)} interview reports for user {user_id}")
        return reports

    except Exception as e:
        logger.error(f"Error getting reports for user {user_id}: {e}")
        raise


async def update_interview_report(report: InterviewReport) -> bool:
    """
    Update interview report in Firestore

    Args:
        report (InterviewReport): Updated report data

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        doc_ref = collection.document(str(report.id))

        # Convert to dictionary
        report_data = report.model_dump()

        # Remove the ID from data to avoid conflicts
        report_data.pop("id", None)

        await doc_ref.update(report_data)

        logger.info(f"Interview report {report.id} updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating interview report {report.id}: {e}")
        raise


async def get_user_report_statistics(user_id: str) -> Dict[str, Any]:
    """
    Get statistics about user's interview reports

    Args:
        user_id (str): User ID to get statistics for

    Returns:
        Dict[str, Any]: Report statistics
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        query = collection.where(filter=FieldFilter("user_id", "==", user_id))

        docs = await query.get()

        if not docs:
            return {
                "total_reports": 0,
                "average_overall_score": 0.0,
                "average_communication_score": 0.0,
                "average_technical_score": 0.0,
                "average_behavioral_score": 0.0,
                "best_score": 0.0,
                "most_recent_score": 0.0,
                "improvement_trend": 0.0,
            }

        # Calculate statistics
        total_reports = len(docs)
        overall_scores = []
        communication_scores = []
        technical_scores = []
        behavioral_scores = []
        sorted_reports = []

        for doc in docs:
            data = doc.to_dict()
            overall_scores.append(data.get("overall_score", 0.0))
            communication_scores.append(data.get("communication_score", 0.0))
            technical_scores.append(data.get("technical_score", 0.0))
            behavioral_scores.append(data.get("behavioral_score", 0.0))

            # Add for sorting by date
            sorted_reports.append(
                {
                    "overall_score": data.get("overall_score", 0.0),
                    "generated_at": data.get("generated_at"),
                }
            )

        # Sort reports by date
        sorted_reports.sort(key=lambda x: x["generated_at"] or datetime.min)

        # Calculate averages
        avg_overall = (
            sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
        )
        avg_communication = (
            sum(communication_scores) / len(communication_scores)
            if communication_scores
            else 0.0
        )
        avg_technical = (
            sum(technical_scores) / len(technical_scores) if technical_scores else 0.0
        )
        avg_behavioral = (
            sum(behavioral_scores) / len(behavioral_scores)
            if behavioral_scores
            else 0.0
        )

        # Best score
        best_score = max(overall_scores) if overall_scores else 0.0

        # Most recent score
        most_recent_score = (
            sorted_reports[-1]["overall_score"] if sorted_reports else 0.0
        )

        # Calculate improvement trend (comparing first half vs second half)
        improvement_trend = 0.0
        if len(sorted_reports) >= 4:
            mid_point = len(sorted_reports) // 2
            first_half_avg = (
                sum(r["overall_score"] for r in sorted_reports[:mid_point]) / mid_point
            )
            second_half_avg = sum(
                r["overall_score"] for r in sorted_reports[mid_point:]
            ) / (len(sorted_reports) - mid_point)
            improvement_trend = second_half_avg - first_half_avg

        statistics = {
            "total_reports": total_reports,
            "average_overall_score": round(avg_overall, 2),
            "average_communication_score": round(avg_communication, 2),
            "average_technical_score": round(avg_technical, 2),
            "average_behavioral_score": round(avg_behavioral, 2),
            "best_score": round(best_score, 2),
            "most_recent_score": round(most_recent_score, 2),
            "improvement_trend": round(improvement_trend, 2),
        }

        logger.info(f"Generated report statistics for user {user_id}")
        return statistics

    except Exception as e:
        logger.error(f"Error getting report statistics for user {user_id}: {e}")
        raise


async def get_reports_by_score_range(
    min_score: float, max_score: float, user_id: Optional[str] = None, limit: int = 50
) -> List[InterviewReport]:
    """
    Get reports within a specific score range

    Args:
        min_score (float): Minimum overall score
        max_score (float): Maximum overall score
        user_id (Optional[str]): Optional user filter
        limit (int): Maximum results to return

    Returns:
        List[InterviewReport]: Reports within score range
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])
        query = (
            collection.where(filter=FieldFilter("overall_score", ">=", min_score))
            .where(filter=FieldFilter("overall_score", "<=", max_score))
            .order_by("overall_score", direction=Query.DESCENDING)
            .limit(limit)
        )

        if user_id:
            query = query.where(filter=FieldFilter("user_id", "==", user_id))

        docs = await query.get()

        reports = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Convert timestamps
            if data.get("generated_at"):
                data["generated_at"] = data["generated_at"].replace(tzinfo=None)

            reports.append(InterviewReport(**data))

        logger.info(
            f"Retrieved {len(reports)} reports with scores between {min_score} and {max_score}"
        )
        return reports

    except Exception as e:
        logger.error(f"Error getting reports by score range: {e}")
        raise


async def get_recent_reports(days: int = 30, limit: int = 100) -> List[InterviewReport]:
    """
    Get recent interview reports

    Args:
        days (int): Number of days to look back
        limit (int): Maximum results to return

    Returns:
        List[InterviewReport]: Recent interview reports
    """
    try:
        collection = get_collection(COLLECTIONS["interview_reports"])

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = (
            collection.where(filter=FieldFilter("generated_at", ">=", cutoff_date))
            .order_by("generated_at", direction=Query.DESCENDING)
            .limit(limit)
        )

        docs = await query.get()

        reports = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Convert timestamps
            if data.get("generated_at"):
                data["generated_at"] = data["generated_at"].replace(tzinfo=None)

            reports.append(InterviewReport(**data))

        logger.info(f"Retrieved {len(reports)} recent reports from last {days} days")
        return reports

    except Exception as e:
        logger.error(f"Error getting recent reports: {e}")
        raise
