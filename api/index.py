"""
Vercel serverless function handler for NavigAI API
"""

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


# Vercel handler function
def handler(request, context=None):
    """Handler function for Vercel serverless deployment"""
    return app(request)


# For compatibility with different calling conventions
def lambda_handler(event, context):
    """AWS Lambda compatibility handler"""
    return handler(event, context)


# For direct ASGI compatibility
application = app

# Export the app for Vercel
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
