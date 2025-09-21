import sys
import os
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

# Load environment variables
from dotenv import load_dotenv

env_path = current_dir.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Import the Quart app
from server import create_app

# Create the app instance
app = create_app()
