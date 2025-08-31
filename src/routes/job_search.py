from quart import Blueprint, request, jsonify
from models.job_search import StudentProfile
from services.job_search_service import find_relevant_jobs

job_search_router = Blueprint("job_search", __name__, url_prefix="/api/v1/jobs")


@job_search_router.route("/search", methods=["POST"])
async def search_jobs():
    """API endpoint to trigger a job search based on a student profile."""

    try:
        student_data = await request.get_json()
        if not student_data:
            return jsonify({"error": "Request body must be a valid JSON"}), 400

        user_id = student_data.pop("userId", None)
        if not user_id:
            return jsonify({"error": "Request body must include a 'userId'"}), 400

        profile = StudentProfile(**student_data)

    except Exception as e:
        return jsonify({"error": "Invalid input data", "details": str(e)}), 400

    results = await find_relevant_jobs(profile, user_id)

    if "error" in results:
        return jsonify(results), 500

    return jsonify(results), 200
