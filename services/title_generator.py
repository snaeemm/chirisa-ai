"""Service for generating session titles using LLM."""

import streamlit as st
from google.genai import Client, types

from config.settings import (
    TITLE_GENERATION_MODEL,
    TITLE_MAX_LENGTH,
    TITLE_MAX_TOKENS,
    TITLE_TEMPERATURE,
)


@st.cache_resource
def get_genai_client() -> Client:
    """Initialize and cache Google GenAI client."""
    return Client()


def generate_session_title(user_message: str) -> str:
    """
    Generate a concise session title based on the first user message.

    Args:
        user_message: The first message from the user

    Returns:
        Generated title (3-5 words) or truncated message as fallback
    """
    try:
        client = get_genai_client()
        prompt = f"""Generate a very short title (3-5 words max) for a \
chat session based on this user message:
"{user_message}"

Only return the title, nothing else. Make it concise and descriptive."""

        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        response = client.models.generate_content(
            model=TITLE_GENERATION_MODEL,
            contents=content,
            config=types.GenerateContentConfig(
                temperature=TITLE_TEMPERATURE,
                max_output_tokens=TITLE_MAX_TOKENS,
            ),
        )

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            text = response.candidates[0].content.parts[0].text
            if text:
                return text.strip().strip('"\'')
    except (AttributeError, IndexError, ValueError) as e:
        st.error(f"Error generating title: {e}")

    # Fallback to truncated message
    if len(user_message) > TITLE_MAX_LENGTH:
        return user_message[:TITLE_MAX_LENGTH] + "..."
    return user_message
