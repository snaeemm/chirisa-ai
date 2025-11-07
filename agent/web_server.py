"""
ADK Web Server with PostgreSQL Session Isolation
Clean ADK interface with fully isolated sessions stored in Neon
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv('DATABASE_URL')
AGENTS_DIR = str(Path(__file__).parent.parent)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in .env")

# Create FastAPI app with full session isolation
# Each session_id gets isolated context - no overlap between conversations
app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_service_uri=DATABASE_URL,
    web=True,
    host="0.0.0.0",
    port=8000
)


if __name__ == "__main__":
    import uvicorn
    print("🚀 Data Center Analyzer with PostgreSQL Sessions")
    print("📊 Main UI: http://localhost:8000/chat")
    print("🔌 API Docs: http://localhost:8000/docs")
    print("💾 Sessions: Fully isolated, stored in PostgreSQL (Neon)")

    uvicorn.run(app, host="0.0.0.0", port=8000)
