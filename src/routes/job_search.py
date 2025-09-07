from quart import Blueprint, request, jsonify
from quart_jwt_extended import jwt_required, get_jwt_identity
from models.job_search import StudentProfile
from services.job_search_service import find_relevant_jobs

job_search_router = Blueprint("job_search", __name__, url_prefix="/api/v1/jobs")


@job_search_router.route("/search", methods=["POST"])
@jwt_required
async def search_jobs():
    try:
        student_data = await request.get_json()
        if not student_data:
            return jsonify({"error": "Request body must be a valid JSON"}), 400

        user_id = get_jwt_identity()
        profile = StudentProfile(**student_data)

    except Exception as e:
        return jsonify({"error": "Invalid input data", "details": str(e)}), 400

    results = await find_relevant_jobs(profile, user_id)

    if "error" in results:
        return jsonify(results), 500

    return jsonify(results), 200
