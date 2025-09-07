import logging
from quart import Blueprint, request, jsonify
import bcrypt
from quart_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from db import (
    create_user_profile,
    get_user_profile,
    get_user_by_email,
    update_user_profile,
)
from models.user import UserProfile

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
async def register_user():
    try:
        data = await request.get_json()
        if (
            not data
            or not data.get("email")
            or not data.get("password")
            or not data.get("full_name")
        ):
            return (
                jsonify({"error": "email, password, and full_name are required"}),
                400,
            )

        if await get_user_by_email(data["email"]):
            return jsonify({"error": "User with this email already exists"}), 409

        hashed_password = bcrypt.hashpw(
            data["password"].encode("utf-8"), bcrypt.gensalt()
        )

        user_profile = UserProfile(
            email=data["email"],
            password=hashed_password.decode("utf-8"),
            full_name=data["full_name"],
            is_approved=False,
        )

        await create_user_profile(user_profile)
        logger.info(f"User registered: {user_profile.email}")
        return (
            jsonify(
                {
                    "message": f"User {user_profile.email} created successfully. Awaiting admin approval."
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/login", methods=["POST"])
async def login_user():
    try:
        data = await request.get_json()
        if not data or not data.get("email") or not data.get("password"):
            return jsonify({"error": "Email and password are required"}), 400

        profile = await get_user_by_email(data["email"])
        if not profile:
            return jsonify({"error": "Invalid credentials"}), 401

        if bcrypt.checkpw(
            data["password"].encode("utf-8"), profile.password.encode("utf-8")
        ):
            if not profile.is_approved:
                logger.warning(f"Login attempt from unapproved user: {profile.email}")
                return (
                    jsonify(
                        {"error": "Your account is pending administrator approval."}
                    ),
                    403,
                )

            access_token = create_access_token(identity=profile.id)
            logger.info(f"User logged in: {profile.email}")
            return jsonify(access_token=access_token)
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/profile", methods=["GET"])
@jwt_required
async def get_my_profile():
    try:
        current_user_id = get_jwt_identity()
        profile = await get_user_profile(current_user_id)
        if not profile:
            return jsonify({"error": "User not found"}), 404

        profile_dict = profile.to_dict()
        del profile_dict["password"]
        return jsonify({"success": True, "data": profile_dict}), 200

    except Exception as e:
        logger.error(f"Error getting user profile for {get_jwt_identity()}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required
async def update_my_profile():
    try:
        current_user_id = get_jwt_identity()
        data = await request.get_json()

        await update_user_profile(current_user_id, data)

        logger.info(f"User profile updated: {current_user_id}")
        return (
            jsonify({"success": True, "message": "Profile updated successfully"}),
            200,
        )

    except Exception as e:
        logger.error(f"Error updating user profile {get_jwt_identity()}: {e}")
        return jsonify({"error": "Internal server error"}), 500
