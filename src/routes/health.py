from quart import Blueprint, Response

health_router = Blueprint("health_router", __name__)


@health_router.route("/health")
async def health_check():
    html_content = "<h1>200 OK</h1>"
    return Response(html_content, mimetype="text/html", status=200)
