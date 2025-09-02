import os
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Global database reference
db = None


def init_firebase():
    """Initialize Firebase with service account credentials"""
    global db

    try:
        if not firebase_admin._apps:
            service_account_path = os.getenv(
                "FIREBASE_SERVICE_ACCOUNT_KEY", "serviceAccountKey.json"
            )

            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully.")

        db = firestore.client()
        print("Firestore connection established.")

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        print(f"Error initializing Firebase: {e}")
        raise


# Interview session functions
def save_interview_session(session_data: Dict[str, Any]) -> bool:
    """Save interview session to Firestore"""
    try:
        if db is None:
            init_firebase()

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
        if db is None:
            init_firebase()

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
        if db is None:
            init_firebase()

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
        if db is None:
            init_firebase()

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


# Interview report functions
def save_interview_report(report_data: Dict[str, Any]) -> bool:
    """Save interview report to Firestore"""
    try:
        if db is None:
            init_firebase()

        # Add timestamp
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
        if db is None:
            init_firebase()

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


# User management functions
def get_user_sessions(candidate_id: str) -> List[Dict[str, Any]]:
    """Get all sessions for a specific candidate"""
    try:
        if db is None:
            init_firebase()

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


# Analytics functions
def get_analytics_data(days: int = 30) -> Dict[str, Any]:
    """Get analytics data for the specified time period"""
    try:
        if db is None:
            init_firebase()

        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get sessions in date range
        sessions = []
        docs = (
            db.collection("interview_sessions")
            .where("created_at", ">=", start_date)
            .stream()
        )

        for doc in docs:
            session_data = doc.to_dict()
            session_data["id"] = doc.id
            sessions.append(session_data)

        # Calculate analytics
        total_sessions = len(sessions)
        completed_sessions = len(
            [s for s in sessions if s.get("status") == "completed"]
        )

        # Calculate average scores
        technical_scores = []
        communication_scores = []

        for session in sessions:
            if session.get("performance_metrics"):
                metrics = session["performance_metrics"]
                technical_scores.append(metrics.get("technical_score", 0))
                communication_scores.append(metrics.get("communication_score", 0))

        avg_technical = (
            sum(technical_scores) / len(technical_scores) if technical_scores else 0
        )
        avg_communication = (
            sum(communication_scores) / len(communication_scores)
            if communication_scores
            else 0
        )

        analytics_data = {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (
                (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
            ),
            "average_technical_score": avg_technical,
            "average_communication_score": avg_communication,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }

        print(f"Analytics data retrieved for {days} days")
        return analytics_data

    except Exception as e:
        logger.error(f"Failed to get analytics data: {e}")
        return {}


# Health check function
def health_check() -> Dict[str, Any]:
    """Check Firebase connection health"""
    try:
        health_status = {
            "firebase_connected": False,
            "firestore_connected": False,
            "error": None,
        }

        # Check Firebase connection
        if firebase_admin._apps:
            health_status["firebase_connected"] = True

            # Check Firestore
            try:
                if db is None:
                    init_firebase()

                test_doc = db.collection("health_check").document("test")
                test_doc.set({"timestamp": datetime.now(), "status": "ok"})
                test_doc.delete()
                health_status["firestore_connected"] = True
                print("✅ Firebase health check passed")
            except Exception as e:
                health_status["error"] = f"Firestore error: {str(e)}"
                print(f"❌ Firestore health check failed: {e}")

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "firebase_connected": False,
            "firestore_connected": False,
            "error": str(e),
        }


# Cleanup function
def delete_interview_session(session_id: str) -> bool:
    """Delete interview session and related data"""
    try:
        if db is None:
            init_firebase()

        # Delete session
        doc_ref = db.collection("interview_sessions").document(session_id)
        doc_ref.delete()

        # Delete report if exists
        report_ref = db.collection("interview_reports").document(session_id)
        report_ref.delete()

        print(f"Interview session deleted: {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete interview session: {e}")
        return False
