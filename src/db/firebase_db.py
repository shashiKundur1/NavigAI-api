"""
Firebase database module for the AI Mock Interview System
This module provides a unified interface to all Firebase operations
"""

# Import all submodules
from .firebase_init import init_firebase, get_db, health_check
from .interview_sessions import (
    save_interview_session,
    get_interview_session,
    update_interview_session,
    get_all_interview_sessions,
    delete_interview_session,
)
from .interview_reports import (
    save_interview_report,
    get_interview_report,
    get_all_interview_reports,
    delete_interview_report,
)
from .user_management import (
    get_user_sessions,
    get_user_reports,
    create_user_profile,
    get_user_profile,
)
from .analytics import get_analytics_data, get_performance_trends, get_job_analytics

# Export all functions for easy import
__all__ = [
    # Firebase initialization
    "init_firebase",
    "get_db",
    "health_check",
    # Interview sessions
    "save_interview_session",
    "get_interview_session",
    "update_interview_session",
    "get_all_interview_sessions",
    "delete_interview_session",
    # Interview reports
    "save_interview_report",
    "get_interview_report",
    "get_all_interview_reports",
    "delete_interview_report",
    # User management
    "get_user_sessions",
    "get_user_reports",
    "create_user_profile",
    "get_user_profile",
    # Analytics
    "get_analytics_data",
    "get_performance_trends",
    "get_job_analytics",
]

# Initialize Firebase on module import
try:
    init_firebase()
except Exception as e:
    print(f"Firebase initialization failed: {e}")
