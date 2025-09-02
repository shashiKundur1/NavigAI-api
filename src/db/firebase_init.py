import os
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any
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
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        print(f"Error initializing Firebase: {e}")
        raise


def get_db():
    """Get Firestore database instance"""
    global db
    if db is None:
        init_firebase()
    return db


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
                db_instance = get_db()
                test_doc = db_instance.collection("health_check").document("test")
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
