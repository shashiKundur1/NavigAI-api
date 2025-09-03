# src/firebase_db/firebase_init.py
"""
Firebase initialization and connection management for NavigAI
"""

import os
import logging
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: Optional[firebase_admin.App] = None
_firestore_client: Optional[Client] = None


def init_firebase() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK

    Returns:
        firebase_admin.App: The initialized Firebase app
    """
    global _firebase_app, _firestore_client

    try:
        # Check if already initialized
        if _firebase_app is not None:
            logger.info("Firebase already initialized")
            return _firebase_app

        # Get Firebase configuration from environment
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

        if not firebase_project_id:
            raise ValueError("FIREBASE_PROJECT_ID environment variable is required")

        # Initialize with service account key file if provided
        if firebase_credentials_path and os.path.exists(firebase_credentials_path):
            logger.info(
                f"Initializing Firebase with service account: {firebase_credentials_path}"
            )
            cred = credentials.Certificate(firebase_credentials_path)
            _firebase_app = firebase_admin.initialize_app(
                cred, {"projectId": firebase_project_id}
            )
        else:
            # Use default credentials (for Google Cloud environment)
            logger.info("Initializing Firebase with default credentials")
            try:
                _firebase_app = firebase_admin.initialize_app(
                    options={"projectId": firebase_project_id}
                )
            except Exception as e:
                logger.warning(f"Failed to initialize with default credentials: {e}")
                # Try with Application Default Credentials
                cred = credentials.ApplicationDefault()
                _firebase_app = firebase_admin.initialize_app(
                    cred, {"projectId": firebase_project_id}
                )

        # Initialize Firestore client
        _firestore_client = firestore.client(_firebase_app)

        logger.info(
            f"Firebase initialized successfully for project: {firebase_project_id}"
        )
        return _firebase_app

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


def get_db() -> Client:
    """
    Get the Firestore database client

    Returns:
        Client: The Firestore client instance
    """
    global _firestore_client

    if _firestore_client is None:
        # Try to initialize if not done yet
        init_firebase()

    if _firestore_client is None:
        raise RuntimeError("Firestore client is not initialized")

    return _firestore_client


def get_firebase_app() -> Optional[firebase_admin.App]:
    """
    Get the Firebase app instance

    Returns:
        Optional[firebase_admin.App]: The Firebase app instance
    """
    return _firebase_app


async def health_check() -> Dict[str, Any]:
    """
    Perform health check on Firebase connection

    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        db = get_db()

        # Try to read a simple document to test connection
        test_doc_ref = db.collection("_health_check").document("test")

        # Write a test document
        await test_doc_ref.set(
            {"timestamp": firestore.SERVER_TIMESTAMP, "status": "healthy"}
        )

        # Read it back
        doc = await test_doc_ref.get()

        if doc.exists:
            # Clean up test document
            await test_doc_ref.delete()

            return {
                "status": "healthy",
                "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "connection": "active",
                "timestamp": doc.to_dict().get("timestamp"),
            }
        else:
            return {"status": "unhealthy", "error": "Failed to read test document"}

    except Exception as e:
        logger.error(f"Firebase health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def close_firebase():
    """
    Close Firebase connection and clean up resources
    """
    global _firebase_app, _firestore_client

    try:
        if _firebase_app:
            firebase_admin.delete_app(_firebase_app)
            _firebase_app = None
            _firestore_client = None
            logger.info("Firebase connection closed")
    except Exception as e:
        logger.error(f"Error closing Firebase connection: {e}")


# Firestore collection references
COLLECTIONS = {
    "interview_sessions": "interview_sessions",
    "interview_reports": "interview_reports",
    "user_profiles": "user_profiles",
    "user_sessions": "user_sessions",
    "user_analytics": "user_analytics",
    "interview_questions": "interview_questions",
    "candidate_responses": "candidate_responses",
    "interview_feedback": "interview_feedback",
}


def get_collection(collection_name: str):
    """
    Get a Firestore collection reference

    Args:
        collection_name (str): Name of the collection

    Returns:
        CollectionReference: Firestore collection reference
    """
    db = get_db()

    if collection_name not in COLLECTIONS:
        logger.warning(
            f"Collection '{collection_name}' not found in predefined collections"
        )

    return db.collection(collection_name)


# Helper functions for common operations
async def batch_write(operations: list) -> bool:
    """
    Perform batch write operations

    Args:
        operations (list): List of operations to perform

    Returns:
        bool: Success status
    """
    try:
        db = get_db()
        batch = db.batch()

        for operation in operations:
            op_type = operation.get("type")
            doc_ref = operation.get("doc_ref")
            data = operation.get("data", {})

            if op_type == "set":
                batch.set(doc_ref, data)
            elif op_type == "update":
                batch.update(doc_ref, data)
            elif op_type == "delete":
                batch.delete(doc_ref)

        await batch.commit()
        logger.info(
            f"Batch write completed successfully with {len(operations)} operations"
        )
        return True

    except Exception as e:
        logger.error(f"Batch write failed: {e}")
        return False


async def transaction_update(doc_ref, update_function):
    """
    Perform transactional update

    Args:
        doc_ref: Document reference
        update_function: Function that takes current data and returns updated data

    Returns:
        bool: Success status
    """
    try:
        db = get_db()

        @firestore.transactional
        async def update_in_transaction(transaction, doc_ref):
            doc = await doc_ref.get(transaction=transaction)

            if doc.exists:
                current_data = doc.to_dict()
                updated_data = update_function(current_data)
                transaction.update(doc_ref, updated_data)
            else:
                # Document doesn't exist, create it
                new_data = update_function({})
                transaction.set(doc_ref, new_data)

        transaction = db.transaction()
        await update_in_transaction(transaction, doc_ref)

        logger.info("Transactional update completed successfully")
        return True

    except Exception as e:
        logger.error(f"Transactional update failed: {e}")
        return False


# Error handling utilities
class FirebaseError(Exception):
    """Custom Firebase error class"""

    pass


class DocumentNotFoundError(FirebaseError):
    """Error when document is not found"""

    pass


class ValidationError(FirebaseError):
    """Error when data validation fails"""

    pass


def handle_firebase_error(e: Exception) -> FirebaseError:
    """
    Convert Firebase exceptions to custom error types

    Args:
        e (Exception): Original exception

    Returns:
        FirebaseError: Converted custom error
    """
    error_message = str(e)

    if "not found" in error_message.lower():
        return DocumentNotFoundError(error_message)
    elif "validation" in error_message.lower():
        return ValidationError(error_message)
    else:
        return FirebaseError(error_message)
