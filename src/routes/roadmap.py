from quart import Blueprint, request, jsonify, Response
from models.roadmap import RoadmapRequest
from services.roadmap_service import generate_student_roadmap

roadmap_router = Blueprint("roadmap", __name__, url_prefix="/api/v1/roadmap")


@roadmap_router.route("/generate", methods=["POST"])
async def generate_roadmap_endpoint():
    """API endpoint to generate and retrieve a student's learning roadmap."""
    try:
        data = await request.get_json()
        req = RoadmapRequest(**data)
    except Exception as e:
        return jsonify({"error": "Invalid input data", "details": str(e)}), 400

    try:
        roadmap_html = await generate_student_roadmap(req.user_id)
        return Response(roadmap_html, content_type="text/html")
    except Exception as e:
        return jsonify({"error": "Failed to generate roadmap", "details": str(e)}), 500
