"""
Configuration settings for the NavigAI system
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings class"""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")

    # Model Settings
    WHISPER_MODEL: str = os.getenv(
        "WHISPER_MODEL", "base"
    )  # Options: "tiny", "base", "small", "medium", "large"

    # Audio Settings
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
    RECORDING_TIMEOUT: int = int(
        os.getenv("RECORDING_TIMEOUT", "120")
    )  # Maximum recording time in seconds
    SILENCE_THRESHOLD: int = int(
        os.getenv("SILENCE_THRESHOLD", "3")
    )  # Silence detection threshold in seconds

    # Interview Settings
    MAX_QUESTIONS: int = int(
        os.getenv("MAX_QUESTIONS", "20")
    )  # Maximum number of questions in an interview

    # Firebase Settings
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")

    # UI Settings
    UI_THEME: str = os.getenv("UI_THEME", "dark")
    UI_COLOR: str = os.getenv("UI_COLOR", "blue")

    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/navigai.log")

    @classmethod
    def load_from_file(cls, file_path: str = "settings.json") -> None:
        """Load settings from a JSON file"""
        try:
            settings_path = Path(file_path)
            if settings_path.exists():
                with open(settings_path, "r") as f:
                    settings_data = json.load(f)

                # Update class attributes with loaded settings
                for key, value in settings_data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)
        except Exception as e:
            print(f"Error loading settings: {e}")

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            "GEMINI_API_KEY": cls.GEMINI_API_KEY,
            "FIREBASE_API_KEY": cls.FIREBASE_API_KEY,
            "WHISPER_MODEL": cls.WHISPER_MODEL,
            "SAMPLE_RATE": cls.SAMPLE_RATE,
            "RECORDING_TIMEOUT": cls.RECORDING_TIMEOUT,
            "SILENCE_THRESHOLD": cls.SILENCE_THRESHOLD,
            "MAX_QUESTIONS": cls.MAX_QUESTIONS,
            "FIREBASE_PROJECT_ID": cls.FIREBASE_PROJECT_ID,
            "UI_THEME": cls.UI_THEME,
            "UI_COLOR": cls.UI_COLOR,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "LOG_FILE": cls.LOG_FILE,
        }


# Load settings from file if it exists
Settings.load_from_file()
