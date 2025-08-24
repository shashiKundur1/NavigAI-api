import os
from dotenv import load_dotenv

load_dotenv()

_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in _allowed_origins_str.split(",") if origin
]
