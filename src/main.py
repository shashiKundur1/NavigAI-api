"""
Main application entry point for the NavigAI API Server
"""

import sys
import os
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Import core components
from core.logging_config import setup_logging


def main():
    """Main function to run the API server"""
    try:
        # Setup logging
        setup_logging()
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Starting NavigAI API Server")

        # Verify API key is loaded
        from core.settings import Settings

        if not Settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set in the environment variables.")
            print("ERROR: GEMINI_API_KEY is not set in the environment variables.")
            sys.exit(1)

        # Start the server directly with uvicorn
        uvicorn.run(
            "server:app", app_dir="src", host="localhost", port=5000, reload=True
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Application error: {e}")
        print(f"ERROR: Failed to start application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
