"""
Firebase database module for the AI Mock Interview System
This module provides a unified interface to all Firebase operations
"""

# Import all submodules
from .firebase_init import (
    init_firebase,
    get_db,
    health_check,
    get_firebase_app,
    close_firebase,
    get_collection,
    batch_write,
    transaction_update,
    COLLECTIONS,
    FirebaseError,
    DocumentNotFoundError,
    ValidationError,
    handle_firebase_error,
)

from .interview_sessions import (
    save_interview_session,
    get_interview_session,
    update_interview_session,
    get_all_interview_sessions,
    delete_interview_session,
    get_sessions_by_user,
    update_session_status,
    get_sessions_by_status,
    count_user_sessions,
    search_sessions,
)

from .interview_reports import (
    save_interview_report,
    get_interview_report,
    get_report_by_session_id,
    get_all_interview_reports,
    delete_interview_report,
    get_reports_by_user,
    update_interview_report,
    get_user_report_statistics,
    get_reports_by_score_range,
    get_recent_reports,
)

from .user_management import (
    create_user_profile,
    get_user_profile,
    get_user_by_email,
    update_user_profile,
    delete_user_profile,
    get_user_sessions,
    get_user_reports,
    create_user_session,
    validate_user_session,
    logout_user_session,
    update_last_login,
    get_users_by_role,
    update_user_subscription,
    search_users,
    cleanup_user_data,
    get_user_statistics,
)

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

from .analytics import (
    get_analytics_data,
    get_performance_trends,
    get_job_analytics,
    save_user_analytics,
    update_user_analytics,
    get_platform_analytics,
    get_interview_trends,
    calculate_improvement_score,
)

# Export all functions for easy import
__all__ = [
    # Firebase initialization
    "init_firebase",
    "get_db",
    "health_check",
    "get_firebase_app",
    "close_firebase",
    "get_collection",
    "batch_write",
    "transaction_update",
    "COLLECTIONS",
    # Error handling
    "FirebaseError",
    "DocumentNotFoundError",
    "ValidationError",
    "handle_firebase_error",
    # Interview sessions
    "save_interview_session",
    "get_interview_session",
    "update_interview_session",
    "get_all_interview_sessions",
    "delete_interview_session",
    "get_sessions_by_user",
    "update_session_status",
    "get_sessions_by_status",
    "count_user_sessions",
    "search_sessions",
    # Interview reports
    "save_interview_report",
    "get_interview_report",
    "get_report_by_session_id",
    "get_all_interview_reports",
    "delete_interview_report",
    "get_reports_by_user",
    "update_interview_report",
    "get_user_report_statistics",
    "get_reports_by_score_range",
    "get_recent_reports",
    # User management
    "create_user_profile",
    "get_user_profile",
    "get_user_by_email",
    "update_user_profile",
    "delete_user_profile",
    "get_user_sessions",
    "get_user_reports",
    "create_user_session",
    "validate_user_session",
    "logout_user_session",
    "update_last_login",
    "get_users_by_role",
    "update_user_subscription",
    "search_users",
    "cleanup_user_data",
    "get_user_statistics",
    # Analytics
    "get_analytics_data",
    "get_performance_trends",
    "get_job_analytics",
    "save_user_analytics",
    "update_user_analytics",
    "get_platform_analytics",
    "get_interview_trends",
    "calculate_improvement_score",
]

# Initialize Firebase on module import
try:
    init_firebase()
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"⚠️ Firebase initialization failed: {e}")
    print("Some Firebase-dependent features may not work properly")

# Version info
__version__ = "1.0.0"
__author__ = "NavigAI Team"
__description__ = "Firebase database operations for NavigAI interview platform"

# Configuration
DEFAULT_COLLECTION_NAMES = COLLECTIONS


# Helper function for common operations
async def get_document_count(collection_name: str) -> int:
    """
    Get total count of documents in a collection

    Args:
        collection_name (str): Name of the collection

    Returns:
        int: Number of documents
    """
    try:
        collection = get_collection(collection_name)
        docs = await collection.get()
        return len(docs)
    except Exception as e:
        logger.error(f"Error getting document count for {collection_name}: {e}")
        return 0


async def check_document_exists(collection_name: str, document_id: str) -> bool:
    """
    Check if a document exists in a collection

    Args:
        collection_name (str): Name of the collection
        document_id (str): Document ID to check

    Returns:
        bool: True if document exists
    """
    try:
        collection = get_collection(collection_name)
        doc = await collection.document(document_id).get()
        return doc.exists
    except Exception as e:
        logger.error(f"Error checking document existence: {e}")
        return False


# Database status check
async def get_database_status() -> Dict[str, Any]:
    """
    Get comprehensive database status

    Returns:
        Dict[str, Any]: Database status information
    """
    try:
        status = await health_check()

        # Add collection counts
        collection_counts = {}
        for collection_name in COLLECTIONS.values():
            try:
                count = await get_document_count(collection_name)
                collection_counts[collection_name] = count
            except:
                collection_counts[collection_name] = "error"

        status.update(
            {
                "collection_counts": collection_counts,
                "total_collections": len(COLLECTIONS),
                "database_version": __version__,
            }
        )

        return status

    except Exception as e:
        return {"status": "error", "error": str(e), "database_version": __version__}


# Utility functions for data validation
def validate_user_id(user_id: str) -> bool:
    """Validate user ID format"""
    return isinstance(user_id, str) and len(user_id) > 0


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format"""
    return isinstance(session_id, str) and len(session_id) > 0
