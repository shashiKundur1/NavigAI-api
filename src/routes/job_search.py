from quart import Blueprint, request, jsonify
from models.job_search import StudentProfile
from services.job_search_service import find_relevant_jobs

job_search_router = Blueprint("job_search", __name__, url_prefix="/api/v1/jobs")


@job_search_router.route("/search", methods=["POST", "OPTIONS"])
async def search_jobs():
    if request.method == "OPTIONS":
        from quart import Response

        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        student_data = await request.get_json()
        if not student_data:
            response = jsonify({"error": "Request body must be a valid JSON"})
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response, 400

        # For prototype, use a default user_id
        user_id = "prototype_user"
        profile = StudentProfile(**student_data)

        results = await find_relevant_jobs(profile, user_id)

        if "error" in results:
            response = jsonify(results)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response, 500

        response = jsonify(results)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response, 200

    except Exception as e:
        response = jsonify({"error": "Invalid input data", "details": str(e)})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response, 400
