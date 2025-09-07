import logging
from quart import Blueprint, request, jsonify
from quart_jwt_extended import jwt_required, get_jwt_identity
from services.interview_service import InterviewService
from db import get_interview_report, get_user_sessions

logger = logging.getLogger(__name__)
interview_bp = Blueprint("interview", __name__)
interview_service = InterviewService()


@interview_bp.route("/create", methods=["POST"])
@jwt_required
async def create_interview():
    try:
        data = await request.get_json()
        if "job_title" not in data:
            return jsonify({"error": "Missing required field: job_title"}), 400

        user_id = get_jwt_identity()
        session_data = await interview_service.create_interview_session(
            user_id=user_id,
            job_title=data["job_title"],
            job_description=data.get("job_description", ""),
            company_name=data.get("company_name", ""),
        )
        return jsonify({"success": True, "data": session_data}), 201
    except Exception as e:
        logger.error(f"Error creating interview: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/start/<session_id>", methods=["POST"])
@jwt_required
async def start_interview(session_id: str):
    try:
        session_data = await interview_service.start_interview_session(session_id)
        return jsonify({"success": True, "data": session_data}), 200
    except Exception as e:
        logger.error(f"Error starting interview {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/status/<session_id>", methods=["GET"])
@jwt_required
async def get_interview_status(session_id: str):
    try:
        status_data = await interview_service.get_session_status(session_id)
        return jsonify({"success": True, "data": status_data}), 200
    except Exception as e:
        logger.error(f"Error getting interview status {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/response/<session_id>", methods=["POST"])
@jwt_required
async def record_response(session_id: str):
    try:
        data = await request.get_json()
        if "question_id" not in data or "response_text" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        response_data = await interview_service.record_candidate_response(
            session_id=session_id,
            question_id=data["question_id"],
            response_text=data["response_text"],
        )
        return jsonify({"success": True, "data": response_data}), 200
    except Exception as e:
        logger.error(f"Error recording response for {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/complete/<session_id>", methods=["POST"])
@jwt_required
async def complete_interview(session_id: str):
    try:
        completion_data = await interview_service.complete_interview_session(session_id)
        return jsonify({"success": True, "data": completion_data}), 200
    except Exception as e:
        logger.error(f"Error completing interview {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/report/<session_id>", methods=["GET"])
@jwt_required
async def get_report_by_session(session_id: str):
    try:
        report = await get_interview_report(session_id)
        if not report:
            return jsonify({"error": "Report not found"}), 404
        return jsonify({"success": True, "data": report.to_dict()}), 200
    except Exception as e:
        logger.error(f"Error getting interview report {session_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@interview_bp.route("/sessions", methods=["GET"])
@jwt_required
async def get_my_sessions():
    try:
        user_id = get_jwt_identity()
        sessions = await get_user_sessions(user_id)
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
        logger.error(f"Error getting my sessions: {e}")
        return jsonify({"error": "Internal server error"}), 500
