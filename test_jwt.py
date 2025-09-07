from quart import Quart
from quart_jwt_extended import JWTManager, jwt_required

app = Quart(__name__)
app.config["JWT_SECRET_KEY"] = "test-secret"
jwt = JWTManager(app)


@jwt_required
async def test_function():
    return "test"


if __name__ == "__main__":
    print("JWT test successful")
