from typing import Optional, Dict, Any
import logging
from .firebase_init import get_db

logger = logging.getLogger(__name__)


def save_interview_report(report_data: Dict[str, Any]) -> bool:
    """Save interview report to Firestore"""
    try:
        db = get_db()
        # Add timestamp
        from datetime import datetime

        report_data["created_at"] = datetime.now()
        # Save to Firestore
        doc_ref = db.collection("interview_reports").document(report_data["session_id"])
        doc_ref.set(report_data)
        print(f"Interview report saved: {report_data['session_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to save interview report: {e}")
        return False


def get_interview_report(session_id: str) -> Optional[Dict[str, Any]]:
    """Get interview report from Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection("interview_reports").document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"Interview report not found: {session_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to get interview report: {e}")
        return None


def get_all_interview_reports() -> list:
    """Get all interview reports from Firestore"""
    try:
        db = get_db()
        reports = []
        docs = db.collection("interview_reports").stream()
        for doc in docs:
            report_data = doc.to_dict()
            report_data["id"] = doc.id
            reports.append(report_data)
        print(f"Retrieved {len(reports)} interview reports")
        return reports
    except Exception as e:
        logger.error(f"Failed to get interview reports: {e}")
        return []


def delete_interview_report(session_id: str) -> bool:
    """Delete interview report from Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection("interview_reports").document(session_id)
        doc_ref.delete()
        print(f"Interview report deleted: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete interview report: {e}")
        return False
