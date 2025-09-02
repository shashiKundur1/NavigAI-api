"""
Main application entry point for the NavigAI Mock Interview System
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Import core components
from core.logging_config import setup_logging
from gui.responsive_gui import ResponsiveMockInterviewGUI


def main():
    """Main function to run the application"""
    try:
        # Setup logging
        setup_logging()
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Starting NavigAI Mock Interview System")

        # Verify API key is loaded
        from core.settings import Settings

        if not Settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set in the environment variables.")
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Configuration Error",
                "GEMINI_API_KEY is not set in the environment variables.",
            )
            sys.exit(1)

        # Create and run application
        app = ResponsiveMockInterviewGUI()
        app.run()

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Application error: {e}")
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Application Error", f"Failed to start application: {str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
