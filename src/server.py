import uvicorn
from quart import Quart, Response
from quart_cors import cors

from core.settings import CORS_ALLOWED_ORIGINS

from core.logging_config import setup_logging
from db.firebase import init_firebase
from routes.health import health_router

setup_logging()

app = Quart(__name__)

app = cors(app, allow_origin=CORS_ALLOWED_ORIGINS)


@app.after_request
async def add_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.before_serving
async def startup():
    init_firebase()


app.register_blueprint(health_router)

if __name__ == "__main__":
    uvicorn.run("server:app", app_dir="src", host="localhost", port=5000, reload=True)
