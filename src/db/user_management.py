# src/firebase_db/user_management.py
"""
Firebase operations for user management in NavigAI
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.cloud.firestore import FieldFilter, Query
from google.cloud import firestore
import secrets

from .firebase_init import (
    get_db,
    get_collection,
    COLLECTIONS,
    DocumentNotFoundError,
    ValidationError,
)
from models.user import UserProfile, UserSession, UserRole, SubscriptionType

logger = logging.getLogger(__name__)


async def create_user_profile(profile: UserProfile) -> str:
    """
    Create a new user profile in Firestore

    Args:
        profile (UserProfile): User profile to create

    Returns:
        str: Document ID of created profile
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])

        # Check if user with email already exists
        existing_user = await get_user_by_email(profile.email)
        if existing_user:
            raise ValidationError(f"User with email {profile.email} already exists")

        # Convert profile to dictionary
        profile_data = profile.model_dump()
        profile_data["created_at"] = firestore.SERVER_TIMESTAMP
        profile_data["updated_at"] = firestore.SERVER_TIMESTAMP

        # Save to Firestore
        doc_ref = await collection.add(profile_data)

        logger.info(f"User profile created with ID: {doc_ref[1].id}")
        return doc_ref[1].id

    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        raise


async def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """
    Get user profile by ID

    Args:
        user_id (str): User ID to retrieve

    Returns:
        Optional[UserProfile]: User profile if found
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(user_id)
        doc = await doc_ref.get()

        if not doc.exists:
            logger.warning(f"User profile {user_id} not found")
            return None

        # Convert Firestore data to UserProfile
        data = doc.to_dict()
        data["id"] = doc.id

        # Convert timestamps
        if data.get("created_at"):
            data["created_at"] = data["created_at"].replace(tzinfo=None)
        if data.get("updated_at"):
            data["updated_at"] = data["updated_at"].replace(tzinfo=None)
        if data.get("last_login"):
            data["last_login"] = (
                data["last_login"].replace(tzinfo=None) if data["last_login"] else None
            )
        if data.get("subscription_start"):
            data["subscription_start"] = (
                data["subscription_start"].replace(tzinfo=None)
                if data["subscription_start"]
                else None
            )
        if data.get("subscription_end"):
            data["subscription_end"] = (
                data["subscription_end"].replace(tzinfo=None)
                if data["subscription_end"]
                else None
            )

        return UserProfile(**data)

    except Exception as e:
        logger.error(f"Error getting user profile {user_id}: {e}")
        raise


async def get_user_by_email(email: str) -> Optional[UserProfile]:
    """
    Get user profile by email address

    Args:
        email (str): Email address to search for

    Returns:
        Optional[UserProfile]: User profile if found
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        query = collection.where(filter=FieldFilter("email", "==", email)).limit(1)

        docs = await query.get()

        if not docs:
            return None

        doc = docs[0]
        data = doc.to_dict()
        data["id"] = doc.id

        # Convert timestamps
        if data.get("created_at"):
            data["created_at"] = data["created_at"].replace(tzinfo=None)
        if data.get("updated_at"):
            data["updated_at"] = data["updated_at"].replace(tzinfo=None)
        if data.get("last_login"):
            data["last_login"] = (
                data["last_login"].replace(tzinfo=None) if data["last_login"] else None
            )
        if data.get("subscription_start"):
            data["subscription_start"] = (
                data["subscription_start"].replace(tzinfo=None)
                if data["subscription_start"]
                else None
            )
        if data.get("subscription_end"):
            data["subscription_end"] = (
                data["subscription_end"].replace(tzinfo=None)
                if data["subscription_end"]
                else None
            )

        return UserProfile(**data)

    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        raise


async def update_user_profile(profile: UserProfile) -> bool:
    """
    Update user profile in Firestore

    Args:
        profile (UserProfile): Updated profile data

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(str(profile.id))

        # Convert to dictionary and update timestamp
        profile_data = profile.model_dump()
        profile_data["updated_at"] = firestore.SERVER_TIMESTAMP

        # Remove the ID from data to avoid conflicts
        profile_data.pop("id", None)

        await doc_ref.update(profile_data)

        logger.info(f"User profile {profile.id} updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating user profile {profile.id}: {e}")
        raise


async def delete_user_profile(user_id: str) -> bool:
    """
    Delete user profile from Firestore

    Args:
        user_id (str): User ID to delete

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(user_id)

        # Check if document exists
        doc = await doc_ref.get()
        if not doc.exists:
            logger.warning(f"User profile {user_id} not found for deletion")
            return False

        await doc_ref.delete()

        # Also delete related data (sessions, etc.)
        await cleanup_user_data(user_id)

        logger.info(f"User profile {user_id} deleted successfully")
        return True

    except Exception as e:
        logger.error(f"Error deleting user profile {user_id}: {e}")
        raise


async def get_user_sessions(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all interview sessions for a user

    Args:
        user_id (str): User ID to get sessions for
        limit (int): Maximum number of sessions to return

    Returns:
        List[Dict[str, Any]]: List of interview sessions
    """
    try:
        from .interview_sessions import get_sessions_by_user

        sessions = await get_sessions_by_user(user_id, limit)
        return [session.model_dump() for session in sessions]

    except Exception as e:
        logger.error(f"Error getting user sessions {user_id}: {e}")
        raise


async def get_user_reports(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all interview reports for a user

    Args:
        user_id (str): User ID to get reports for
        limit (int): Maximum number of reports to return

    Returns:
        List[Dict[str, Any]]: List of interview reports
    """
    try:
        from .interview_reports import get_reports_by_user

        reports = await get_reports_by_user(user_id, limit)
        return [report.model_dump() for report in reports]

    except Exception as e:
        logger.error(f"Error getting user reports {user_id}: {e}")
        raise


async def create_user_session(
    user_id: str, ip_address: str = None, user_agent: str = None
) -> str:
    """
    Create a new user session

    Args:
        user_id (str): User ID
        ip_address (str): User's IP address
        user_agent (str): User's browser user agent

    Returns:
        str: Session token
    """
    try:
        collection = get_collection(COLLECTIONS["user_sessions"])

        # Generate session token
        session_token = secrets.token_urlsafe(32)

        session_data = {
            "user_id": user_id,
            "session_token": session_token,
            "login_timestamp": firestore.SERVER_TIMESTAMP,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "is_active": True,
        }

        # Save session
        await collection.add(session_data)

        # Update user's last login
        await update_last_login(user_id)

        logger.info(f"User session created for user {user_id}")
        return session_token

    except Exception as e:
        logger.error(f"Error creating user session: {e}")
        raise


async def validate_user_session(session_token: str) -> Optional[str]:
    """
    Validate user session and return user ID

    Args:
        session_token (str): Session token to validate

    Returns:
        Optional[str]: User ID if session is valid
    """
    try:
        collection = get_collection(COLLECTIONS["user_sessions"])
        query = (
            collection.where(filter=FieldFilter("session_token", "==", session_token))
            .where(filter=FieldFilter("is_active", "==", True))
            .limit(1)
        )

        docs = await query.get()

        if not docs:
            return None

        session_data = docs[0].to_dict()

        # Check if session is expired (24 hours)
        login_time = session_data.get("login_timestamp")
        if login_time:
            if datetime.utcnow() - login_time.replace(tzinfo=None) > timedelta(
                hours=24
            ):
                # Session expired, deactivate it
                await docs[0].reference.update({"is_active": False})
                return None

        return session_data.get("user_id")

    except Exception as e:
        logger.error(f"Error validating user session: {e}")
        raise


async def logout_user_session(session_token: str) -> bool:
    """
    Logout user session

    Args:
        session_token (str): Session token to logout

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["user_sessions"])
        query = (
            collection.where(filter=FieldFilter("session_token", "==", session_token))
            .where(filter=FieldFilter("is_active", "==", True))
            .limit(1)
        )

        docs = await query.get()

        if not docs:
            return False

        # Update session to inactive
        await docs[0].reference.update(
            {"is_active": False, "logout_timestamp": firestore.SERVER_TIMESTAMP}
        )

        logger.info("User session logged out successfully")
        return True

    except Exception as e:
        logger.error(f"Error logging out user session: {e}")
        raise


async def update_last_login(user_id: str) -> bool:
    """
    Update user's last login timestamp

    Args:
        user_id (str): User ID to update

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(user_id)

        await doc_ref.update({"last_login": firestore.SERVER_TIMESTAMP})

        return True

    except Exception as e:
        logger.error(f"Error updating last login for user {user_id}: {e}")
        raise


async def get_users_by_role(role: UserRole, limit: int = 100) -> List[UserProfile]:
    """
    Get users by role

    Args:
        role (UserRole): User role to filter by
        limit (int): Maximum number of users to return

    Returns:
        List[UserProfile]: List of users with specified role
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        query = (
            collection.where(filter=FieldFilter("role", "==", role.value))
            .order_by("created_at", direction=Query.DESCENDING)
            .limit(limit)
        )

        docs = await query.get()

        users = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Convert timestamps
            if data.get("created_at"):
                data["created_at"] = data["created_at"].replace(tzinfo=None)
            if data.get("updated_at"):
                data["updated_at"] = data["updated_at"].replace(tzinfo=None)
            if data.get("last_login"):
                data["last_login"] = (
                    data["last_login"].replace(tzinfo=None)
                    if data["last_login"]
                    else None
                )

            users.append(UserProfile(**data))

        logger.info(f"Retrieved {len(users)} users with role {role.value}")
        return users

    except Exception as e:
        logger.error(f"Error getting users by role {role.value}: {e}")
        raise


async def update_user_subscription(
    user_id: str,
    subscription_type: SubscriptionType,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> bool:
    """
    Update user subscription information

    Args:
        user_id (str): User ID to update
        subscription_type (SubscriptionType): New subscription type
        start_date (Optional[datetime]): Subscription start date
        end_date (Optional[datetime]): Subscription end date

    Returns:
        bool: Success status
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        doc_ref = collection.document(user_id)

        update_data = {
            "subscription_type": subscription_type.value,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        if start_date:
            update_data["subscription_start"] = start_date

        if end_date:
            update_data["subscription_end"] = end_date

        await doc_ref.update(update_data)

        logger.info(
            f"Updated subscription for user {user_id} to {subscription_type.value}"
        )
        return True

    except Exception as e:
        logger.error(f"Error updating subscription for user {user_id}: {e}")
        raise


async def search_users(
    search_term: str, role_filter: Optional[UserRole] = None, limit: int = 50
) -> List[UserProfile]:
    """
    Search users by name or email

    Args:
        search_term (str): Term to search for
        role_filter (Optional[UserRole]): Optional role filter
        limit (int): Maximum results to return

    Returns:
        List[UserProfile]: Matching user profiles
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])

        query = collection.limit(limit)

        if role_filter:
            query = query.where(filter=FieldFilter("role", "==", role_filter.value))

        docs = await query.get()

        # Filter results in memory (not ideal for large datasets)
        matching_users = []
        search_lower = search_term.lower()

        for doc in docs:
            data = doc.to_dict()
            full_name = data.get("full_name", "").lower()
            email = data.get("email", "").lower()

            if search_lower in full_name or search_lower in email:
                data["id"] = doc.id

                # Convert timestamps
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].replace(tzinfo=None)
                if data.get("updated_at"):
                    data["updated_at"] = data["updated_at"].replace(tzinfo=None)
                if data.get("last_login"):
                    data["last_login"] = (
                        data["last_login"].replace(tzinfo=None)
                        if data["last_login"]
                        else None
                    )

                matching_users.append(UserProfile(**data))

        logger.info(f"Found {len(matching_users)} users matching '{search_term}'")
        return matching_users

    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise


async def cleanup_user_data(user_id: str) -> bool:
    """
    Clean up all data related to a user

    Args:
        user_id (str): User ID to clean up data for

    Returns:
        bool: Success status
    """
    try:
        # Delete user sessions
        sessions_collection = get_collection(COLLECTIONS["user_sessions"])
        sessions_query = sessions_collection.where(
            filter=FieldFilter("user_id", "==", user_id)
        )
        sessions_docs = await sessions_query.get()

        for doc in sessions_docs:
            await doc.reference.delete()

        # Note: Interview sessions and reports are typically kept for audit purposes
        # but you could add similar cleanup logic here if needed

        logger.info(f"Cleaned up data for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error cleaning up data for user {user_id}: {e}")
        raise


async def get_user_statistics() -> Dict[str, Any]:
    """
    Get overall user statistics

    Returns:
        Dict[str, Any]: User statistics
    """
    try:
        collection = get_collection(COLLECTIONS["user_profiles"])
        docs = await collection.get()

        total_users = len(docs)
        role_counts = {role.value: 0 for role in UserRole}
        subscription_counts = {sub.value: 0 for sub in SubscriptionType}
        active_users_30d = 0

        cutoff_date = datetime.utcnow() - timedelta(days=30)

        for doc in docs:
            data = doc.to_dict()

            # Count by role
            role = data.get("role", "candidate")
            if role in role_counts:
                role_counts[role] += 1

            # Count by subscription
            subscription = data.get("subscription_type", "free")
            if subscription in subscription_counts:
                subscription_counts[subscription] += 1

            # Count active users
            last_login = data.get("last_login")
            if last_login and last_login.replace(tzinfo=None) > cutoff_date:
                active_users_30d += 1

        statistics = {
            "total_users": total_users,
            "role_distribution": role_counts,
            "subscription_distribution": subscription_counts,
            "active_users_last_30_days": active_users_30d,
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info("Generated user statistics")
        return statistics

    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        raise
