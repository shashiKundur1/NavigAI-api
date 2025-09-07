from quart import Blueprint, request, jsonify, Response
from quart_jwt_extended import jwt_required, get_jwt_identity
from services.roadmap_service import generate_student_roadmap

roadmap_router = Blueprint("roadmap", __name__, url_prefix="/api/v1/roadmap")


@roadmap_router.route("/generate", methods=["POST"])
@jwt_required
async def generate_roadmap_endpoint():
    try:
        user_id = get_jwt_identity()
        roadmap_html = await generate_student_roadmap(user_id)
        return Response(roadmap_html, content_type="text/html")

    except Exception as e:
        return jsonify({"error": "Failed to generate roadmap", "details": str(e)}), 500
