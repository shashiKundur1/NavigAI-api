import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

sys.path.append(str(Path(__file__).parent.parent))
from core.settings import Settings

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None
_firestore_client: Optional[Client] = None


def init_firebase() -> firebase_admin.App:
    global _firebase_app, _firestore_client

    try:
        if _firebase_app is not None:
            return _firebase_app

        firebase_project_id = Settings.FIREBASE_PROJECT_ID
        firebase_credentials_path = Settings.FIREBASE_CREDENTIALS_PATH

        if not os.path.isabs(firebase_credentials_path):
            project_root = Path(__file__).parent.parent.parent
            firebase_credentials_path = str(project_root / firebase_credentials_path)

        if os.path.exists(firebase_credentials_path):
            cred = credentials.Certificate(firebase_credentials_path)
            _firebase_app = firebase_admin.initialize_app(
                cred, {"projectId": firebase_project_id}
            )
        else:
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(
                cred, {"projectId": firebase_project_id}
            )

        _firestore_client = firestore.client(_firebase_app)
        logger.info(
            f"Firebase initialized successfully for project: {firebase_project_id}"
        )
        return _firebase_app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


def get_db() -> Client:
    global _firestore_client
    if _firestore_client is None:
        init_firebase()
    if _firestore_client is None:
        raise RuntimeError("Firestore client is not initialized")
    return _firestore_client


COLLECTIONS = {
    "interview_sessions": "interview_sessions",
    "interview_reports": "interview_reports",
    "user_profiles": "user_profiles",
    "user_sessions": "user_sessions",
    "user_analytics": "user_analytics",
    "job_searches": "job_searches",
    "roadmaps": "roadmaps",
}


def get_collection(collection_name: str):
    db = get_db()
    if collection_name not in COLLECTIONS:
        logger.warning(
            f"Collection '{collection_name}' not found in predefined collections"
        )
    return db.collection(collection_name)


class FirebaseError(Exception):
    pass


class DocumentNotFoundError(FirebaseError):
    pass


class ValidationError(FirebaseError):
    pass
