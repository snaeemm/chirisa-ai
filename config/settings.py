"""Application configuration and constants."""

# Application settings
APP_NAME = "shaz"
DEFAULT_USER_ID = "default_user"

# Authentication settings (legacy - kept for backwards compatibility)
AUTH_USERNAME = "Admin"
AUTH_PASSWORD = "professional_granite_123!"

# Multi-user authentication
USERS = {
    "Admin": "professional_granite_123!",
    "Colm": "chirisa123",
    "Omar": "chirisa123"
}

# Model settings
DEFAULT_MODEL = "gemini-2.5-flash-preview-09-2025"
TITLE_GENERATION_MODEL = "gemini-2.5-flash-preview-09-2025"
TITLE_MAX_TOKENS = 20
TITLE_TEMPERATURE = 0.7

# Database settings
DATABASE_URL = "postgresql://neondb_owner:npg_oBalGu5gF4Ij@ep-lingering-hall-a8sevpqf-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require"


# UI settings
SESSION_CONTAINER_HEIGHT = 600
TITLE_MAX_LENGTH = 30

# Streamlit page config
PAGE_CONFIG = {
    "page_title": "Ask Shahz",
    "page_icon": "💬",
    "layout": "wide"
}
