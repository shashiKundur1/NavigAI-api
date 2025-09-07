from .firebase_init import init_firebase, get_db
from .interview_sessions import (
    save_interview_session,
    get_interview_session,
    update_interview_session,
    get_all_interview_sessions,
    get_sessions_by_user,
)
from .interview_reports import (
    save_interview_report,
    get_interview_report,
    get_reports_by_user,
)
from .user_management import (
    create_user_profile,
    get_user_profile,
    get_user_by_email,
    update_user_profile,
    get_user_sessions,
    get_user_reports,
)
from .analytics import get_analytics_data
from .job_searches import save_job_search, get_job_searches_by_user
from .roadmaps import save_roadmap

__all__ = [
    "init_firebase",
    "get_db",
    "save_interview_session",
    "get_interview_session",
    "update_interview_session",
    "get_all_interview_sessions",
    "get_sessions_by_user",
    "save_interview_report",
    "get_interview_report",
    "get_reports_by_user",
    "create_user_profile",
    "get_user_profile",
    "get_user_by_email",
    "update_user_profile",
    "get_user_sessions",
    "get_user_reports",
    "get_analytics_data",
    "save_job_search",
    "get_job_searches_by_user",
    "save_roadmap",
]

try:
    init_firebase()
except Exception as e:
    print(f"Firebase initialization failed: {e}")
