# src/navigai_api/routes/interview.py
"""
Interview API routes for the NavigAI system
"""

import logging
from quart import Blueprint, request, jsonify, current_app
from typing import Dict, Any
import datetime

from ..services.interview_service import InterviewService
from ..services.livekit_service import LiveKitService

logger = logging.getLogger(__name__)

interview_bp = Blueprint("interview", __name__)

# Initialize services
interview_service = InterviewService()


@interview_bp.route("/create", methods=["POST"])
async def create_interview():
    """Create a new interview session"""
    try:
        data = await request.get_json()

        # Validate required fields
        required_fields = ["user_id", "job_title"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Create interview session
        session_data = await interview_service.create_interview_session(
            user_id=data["user_id"],
            job_title=data["job_title"],
            job_description=data.get("job_description", ""),
            company_name=data.get("company_name", ""),
            interview_type=data.get("interview_type", "general"),
            difficulty=data.get("difficulty", "medium"),
            estimated_duration=data.get("estimated_duration", 1800),
            max_questions=data.get("max_questions", 10),
        )

        return jsonify({"success": True, "data": session_data}), 201

    except ValueError as e:
        logger.error(f"Validation error creating interview: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating interview: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/start/<session_id>", methods=["POST"])
async def start_interview(session_id: str):
    """Start an interview session"""
    try:
        session_data = await interview_service.start_interview_session(session_id)

        return jsonify({"success": True, "data": session_data}), 200

    except ValueError as e:
        logger.error(f"Validation error starting interview {session_id}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error starting interview {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/status/<session_id>", methods=["GET"])
async def get_interview_status(session_id: str):
    """Get interview session status"""
    try:
        status_data = await interview_service.get_session_status(session_id)

        return jsonify({"success": True, "data": status_data}), 200

    except ValueError as e:
        logger.error(f"Interview {session_id} not found: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting interview status {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/response/<session_id>", methods=["POST"])
async def record_response(session_id: str):
    """Record candidate response to a question"""
    try:
        data = await request.get_json()

        # Validate required fields
        required_fields = ["question_id", "response_text"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        response_data = await interview_service.record_candidate_response(
            session_id=session_id,
            question_id=data["question_id"],
            response_text=data["response_text"],
            response_audio_url=data.get("response_audio_url"),
            response_duration=data.get("response_duration", 0),
        )

        return jsonify({"success": True, "data": response_data}), 200

    except ValueError as e:
        logger.error(f"Validation error recording response for {session_id}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error recording response for {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/complete/<session_id>", methods=["POST"])
async def complete_interview(session_id: str):
    """Complete an interview session"""
    try:
        completion_data = await interview_service.complete_interview_session(session_id)

        return jsonify({"success": True, "data": completion_data}), 200

    except ValueError as e:
        logger.error(f"Validation error completing interview {session_id}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error completing interview {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/pause/<session_id>", methods=["POST"])
async def pause_interview(session_id: str):
    """Pause an interview session"""
    try:
        pause_data = await interview_service.pause_interview_session(session_id)

        return jsonify({"success": True, "data": pause_data}), 200

    except ValueError as e:
        logger.error(f"Validation error pausing interview {session_id}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error pausing interview {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/resume/<session_id>", methods=["POST"])
async def resume_interview(session_id: str):
    """Resume a paused interview session"""
    try:
        resume_data = await interview_service.resume_interview_session(session_id)

        return jsonify({"success": True, "data": resume_data}), 200

    except ValueError as e:
        logger.error(f"Validation error resuming interview {session_id}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error resuming interview {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/report/<session_id>", methods=["GET"])
async def get_interview_report(session_id: str):
    """Get interview report"""
    try:
        from db.firebase_db import get_interview_report

        report = await get_interview_report(session_id)
        if not report:
            return jsonify({"error": "Report not found"}), 404

        return jsonify({"success": True, "data": report.to_dict()}), 200

    except Exception as e:
        logger.error(f"Error getting interview report {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/sessions/<user_id>", methods=["GET"])
async def get_user_sessions(user_id: str):
    """Get all interview sessions for a user"""
    try:
        from db.firebase_db import get_user_sessions

        sessions = await get_user_sessions(user_id)

        # Convert sessions to dict format
        sessions_data = [session.to_dict() for session in sessions]

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "sessions": sessions_data,
                        "total_count": len(sessions_data),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting user sessions {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/analytics/<user_id>", methods=["GET"])
async def get_user_analytics(user_id: str):
    """Get user interview analytics"""
    try:
        from db.firebase_db import get_analytics_data

        analytics = await get_analytics_data(user_id)

        return jsonify({"success": True, "data": analytics}), 200

    except Exception as e:
        logger.error(f"Error getting user analytics {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


# LiveKit specific routes
@interview_bp.route("/livekit/token", methods=["POST"])
async def generate_livekit_token():
    """Generate LiveKit participant token"""
    try:
        data = await request.get_json()

        required_fields = ["room_name", "participant_name"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        livekit_service = LiveKitService()

        token = await livekit_service.generate_participant_token(
            room_name=data["room_name"],
            participant_name=data["participant_name"],
            is_interviewer=data.get("is_interviewer", False),
        )

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "token": token,
                        "room_name": data["room_name"],
                        "participant_name": data["participant_name"],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error generating LiveKit token: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/livekit/room", methods=["POST"])
async def create_livekit_room():
    """Create LiveKit room"""
    try:
        data = await request.get_json()

        if "room_name" not in data:
            return jsonify({"error": "Missing required field: room_name"}), 400

        livekit_service = LiveKitService()

        room_data = await livekit_service.create_room(data["room_name"])

        return jsonify({"success": True, "data": room_data}), 201

    except Exception as e:
        logger.error(f"Error creating LiveKit room: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Health check for interview service
@interview_bp.route("/health", methods=["GET"])
async def interview_health():
    """Health check for interview service"""
    try:
        livekit_service = LiveKitService()
        livekit_health = livekit_service.health_check()

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "service": "interview",
                        "status": "healthy",
                        "livekit": livekit_health,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Interview service health check failed: {e}")
        return (
            jsonify(
                {"success": False, "error": "Service unhealthy", "details": str(e)}
            ),
            500,
        )


# Error handlers
@interview_bp.errorhandler(404)
async def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@interview_bp.errorhandler(405)
async def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@interview_bp.errorhandler(500)
async def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500
