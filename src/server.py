import uvicorn
import os
from quart import Quart, Response
from quart_cors import cors

from core.settings import Settings
from core.logging_config import setup_logging
from db.firebase_init import init_firebase


def create_app():
    setup_logging()
    app = Quart(__name__)
    app = cors(
        app,
        allow_origin=Settings.CORS_ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Configure JWT first
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "your-dev-secret-key"
    )

    # Initialize JWT manager with app
    from extensions import jwt

    jwt.init_app(app)

    # Import and register blueprints AFTER JWT initialization
    from routes.health import health_router
    from routes.auth import auth_bp
    from routes.job_search import job_search_router
    from routes.roadmap import roadmap_router
    from routes.interview import interview_bp

    app.register_blueprint(health_router)
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(job_search_router)
    app.register_blueprint(roadmap_router)
    app.register_blueprint(interview_bp, url_prefix="/api/v1/interview")

    # Quick test endpoint
    @app.route("/api/test", methods=["GET", "POST"])
    async def test():
        return {"status": "ok", "message": "API is working"}

    @app.after_request
    async def add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    @app.before_serving
    async def startup():
        init_firebase()

    return app


app = create_app()


def start_server():
    """Start the NavigAI API server"""
    import os

    host = os.environ.get("HOST", "0.0.0.0")  # Digital Ocean needs 0.0.0.0
    port = int(os.environ.get("PORT", 5000))
    reload = os.environ.get("ENVIRONMENT", "development") == "development"

    uvicorn.run("server:app", app_dir="src", host=host, port=port, reload=reload)


if __name__ == "__main__":
    start_server()
