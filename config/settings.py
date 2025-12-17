"""Application configuration and constants."""
import os

# Application settings
APP_NAME = "shaz"
DEFAULT_USER_ID = "default_user"

# Authentication settings (legacy - kept for backwards compatibility)
AUTH_USERNAME = "Admin"
AUTH_PASSWORD = "professional_granite_123!"

# Multi-user authentication
USERS = {
    "Admin": "professional_granite_123!",
    "shahzeb.naeem": "professional_granite_123!",  # Added shahzeb.naeem
    "Colm": "CaliforniaT_V8!",
    "Omar": "chirisa123",
    "Max": "chirisa123",
    "Tristan": "chirisa123"
}

# Model settings
DEFAULT_MODEL = "gemini-2.5-flash"
TITLE_GENERATION_MODEL = "gemini-2.5-flash"
TITLE_MAX_TOKENS = 20
TITLE_TEMPERATURE = 0.7

# Database settings - use environment variable or default to local PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost:5432/chirisa"
)


# UI settings
SESSION_CONTAINER_HEIGHT = 600
TITLE_MAX_LENGTH = 30

# File upload settings
FILE_UPLOAD_MAX_SIZE_MB = 15
SUPPORTED_FILE_EXTENSIONS = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.doc', '.xls', '.ppt', '.png', '.jpg', '.jpeg']
FILE_UPLOAD_TEMP_DIR = "/tmp/shaz_uploads"
FILE_CLEANUP_INTERVAL_HOURS = 24

# Streamlit page config
PAGE_CONFIG = {
    "page_title": "Ask Shahz",
    "page_icon": "💬",
    "layout": "wide"
}
