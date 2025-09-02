import os
from dotenv import load_dotenv

load_dotenv()

_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in _allowed_origins_str.split(",") if origin
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
THEIR_STACK_API_KEY = os.getenv("THEIR_STACK_API_KEY")


class Settings:
    CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
    GEMINI_API_KEY = GEMINI_API_KEY
    THEIR_STACK_API_KEY = THEIR_STACK_API_KEY
