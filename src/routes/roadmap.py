from quart import Blueprint, request, jsonify, Response
from services.roadmap_service import generate_student_roadmap

roadmap_router = Blueprint("roadmap", __name__, url_prefix="/api/v1/roadmap")


@roadmap_router.route("/generate", methods=["POST", "OPTIONS"])
async def generate_roadmap_endpoint():
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        # For prototype, use a default user_id
        user_id = "prototype_user"
        roadmap_html = await generate_student_roadmap(user_id)
        response = Response(roadmap_html, content_type="text/html")
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except Exception as e:
        response = jsonify({"error": "Failed to generate roadmap", "details": str(e)})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response, 500
