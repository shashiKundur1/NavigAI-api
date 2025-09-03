# src/navigai_api/routes/auth.py
"""
Authentication API routes for the NavigAI system
"""

import logging
from quart import Blueprint, request, jsonify
import datetime

from db.firebase_db import create_user_profile, get_user_profile
from ..models.user import UserProfile, UserRole, SubscriptionType

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
async def register_user():
    """Register a new user"""
    try:
        data = await request.get_json()

        # Validate required fields
        required_fields = ["email", "full_name"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Create user profile
        user_profile = UserProfile(
            email=data["email"],
            full_name=data["full_name"],
            role=UserRole(data.get("role", "candidate")),
            current_job_title=data.get("current_job_title", ""),
            experience_years=data.get("experience_years", 0),
            skills=data.get("skills", []),
            target_roles=data.get("target_roles", []),
            preferred_industries=data.get("preferred_industries", []),
            subscription_type=SubscriptionType(data.get("subscription_type", "free")),
        )

        # Save to Firebase
        await create_user_profile(user_profile)

        logger.info(f"User registered: {user_profile.email}")

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "user_id": user_profile.id,
                        "email": user_profile.email,
                        "full_name": user_profile.full_name,
                        "role": user_profile.role.value,
                        "subscription_type": user_profile.subscription_type.value,
                        "created_at": user_profile.created_at.isoformat(),
                    },
                }
            ),
            201,
        )

    except ValueError as e:
        logger.error(f"Validation error registering user: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/profile/<user_id>", methods=["GET"])
async def get_profile(user_id: str):
    """Get user profile"""
    try:
        profile = await get_user_profile(user_id)
        if not profile:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"success": True, "data": profile.to_dict()}), 200

    except Exception as e:
        logger.error(f"Error getting user profile {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/profile/<user_id>", methods=["PUT"])
async def update_profile(user_id: str):
    """Update user profile"""
    try:
        data = await request.get_json()

        # Get existing profile
        profile = await get_user_profile(user_id)
        if not profile:
            return jsonify({"error": "User not found"}), 404

        # Update fields
        if "full_name" in data:
            profile.full_name = data["full_name"]
        if "current_job_title" in data:
            profile.current_job_title = data["current_job_title"]
        if "experience_years" in data:
            profile.experience_years = data["experience_years"]
        if "skills" in data:
            profile.skills = data["skills"]
        if "target_roles" in data:
            profile.target_roles = data["target_roles"]
        if "preferred_industries" in data:
            profile.preferred_industries = data["preferred_industries"]
        if "interview_goals" in data:
            profile.interview_goals = data["interview_goals"]

        profile.updated_at = datetime.utcnow()

        # Save updated profile
        from db.firebase_db import update_user_profile

        await update_user_profile(profile)

        logger.info(f"User profile updated: {user_id}")

        return jsonify({"success": True, "data": profile.to_dict()}), 200

    except Exception as e:
        logger.error(f"Error updating user profile {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/login", methods=["POST"])
async def login_user():
    """User login (simplified - in production, use proper authentication)"""
    try:
        data = await request.get_json()

        if "email" not in data:
            return jsonify({"error": "Missing required field: email"}), 400

        # Find user by email (simplified lookup)
        from db.firebase_db import get_user_by_email

        profile = await get_user_by_email(data["email"])

        if not profile:
            return jsonify({"error": "User not found"}), 404

        # Update last login
        profile.last_login = datetime.utcnow()
        from db.firebase_db import update_user_profile

        await update_user_profile(profile)

        logger.info(f"User logged in: {profile.email}")

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "user_id": profile.id,
                        "email": profile.email,
                        "full_name": profile.full_name,
                        "role": profile.role.value,
                        "subscription_type": profile.subscription_type.value,
                        "last_login": profile.last_login.isoformat(),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/health", methods=["GET"])
async def auth_health():
    """Health check for auth service"""
    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "service": "auth",
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }
        ),
        200,
    )
