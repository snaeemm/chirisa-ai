"""Service for managing session state and database operations."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import streamlit as st

from config.settings import APP_NAME, DEFAULT_USER_ID, TITLE_MAX_LENGTH
from utils.date_utils import safe_format_timestamp
from utils.event_utils import reconstruct_messages_from_events

if TYPE_CHECKING:
    from google.adk.sessions import DatabaseSessionService

SessionDict = dict[str, Any]


async def retry_session_operation(operation, *args, max_retries=3, **kwargs):
    """Retry wrapper for ADK session service operations"""
    retry_delays = [0.5, 1.0, 2.0]  # Progressive delays in seconds

    for attempt in range(max_retries):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            # Check if it's a database connection error
            error_msg = str(e).lower()
            is_connection_error = any(
                term in error_msg for term in [
                    'connection', 'timeout', 'network', 'database',
                    'postgres', 'psycopg', 'operational'
                ]
            )

            if is_connection_error and attempt < max_retries - 1:
                # Silent retry with progressive delay
                time.sleep(retry_delays[attempt])
                continue
            else:
                # Last attempt or non-connection error, re-raise
                if attempt == max_retries - 1:
                    logging.error(f"Session operation failed after {max_retries} attempts: {str(e)}")
                raise


def load_sessions_from_database(
    session_service: DatabaseSessionService,
) -> dict[str, SessionDict]:
    """
    Load all sessions from the database for the current user.

    Args:
        session_service: The DatabaseSessionService instance

    Returns:
        Dictionary mapping session_id to session data
    """
    try:
        user_id = st.session_state.get("user_id", DEFAULT_USER_ID)

        # List all sessions for this user
        sessions_response = asyncio.run(retry_session_operation(
            session_service.list_sessions,
            app_name=APP_NAME,
            user_id=user_id
        ))

        loaded_sessions: dict[str, SessionDict] = {}

        # Handle different response formats
        if hasattr(sessions_response, "session_ids"):
            session_ids = sessions_response.session_ids  # type: ignore[attr-defined]
        elif hasattr(sessions_response, "sessions"):
            session_ids = [s.id for s in sessions_response.sessions]  # type: ignore[attr-defined]
        elif isinstance(sessions_response, list):
            session_ids = sessions_response
        else:
            session_ids = []

        for session_id in session_ids:
            # Get full session data
            session = asyncio.run(retry_session_operation(
                session_service.get_session,
                app_name=APP_NAME,
                user_id=user_id,
                session_id=str(session_id),  # type: ignore[arg-type]
            ))

            if session:
                # Reconstruct messages from events
                messages = reconstruct_messages_from_events(session.events)

                # Get title from session state or generate from first message
                title = session.state.get("ui_title", "New Chat")
                if title == "New Chat" and messages:
                    # Find first user message
                    first_user_msg = next(
                        (
                            m
                            for m in messages
                            if m["role"] == "user" and "content" in m
                        ),
                        None,
                    )
                    if first_user_msg:
                        content = first_user_msg["content"]
                        title = (
                            content[:TITLE_MAX_LENGTH] + "..."
                            if len(content) > TITLE_MAX_LENGTH
                            else content
                        )

                loaded_sessions[session.id] = {
                    "messages": messages,
                    "created_at": safe_format_timestamp(session.last_update_time),
                    "title": title,
                }
    except (AttributeError, KeyError, ValueError) as e:
        st.error(f"Error loading sessions: {e}")

    return loaded_sessions


def create_new_session(session_service: DatabaseSessionService) -> str:
    """
    Create a new session in the database and session state.

    Args:
        session_service: The DatabaseSessionService instance

    Returns:
        The new session ID
    """
    user_id = st.session_state.get("user_id", DEFAULT_USER_ID)
    new_session_id = f"session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    # Add to session state
    st.session_state.sessions[new_session_id] = {
        "messages": [],
        "created_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "title": "New Chat",
    }

    # Create ADK session
    asyncio.run(retry_session_operation(
        session_service.create_session,
        app_name=APP_NAME,
        user_id=user_id,
        session_id=new_session_id
    ))

    return new_session_id


def initialize_sessions(session_service: DatabaseSessionService) -> None:
    """
    Initialize session state by loading existing sessions or creating a new one.

    Args:
        session_service: The DatabaseSessionService instance
    """
    # Initialize user_id
    if "user_id" not in st.session_state:
        st.session_state.user_id = DEFAULT_USER_ID

    # Load sessions from database on first run
    if "sessions_loaded" not in st.session_state:
        # Load all existing sessions from database
        loaded_sessions = load_sessions_from_database(session_service)
        st.session_state.sessions = loaded_sessions
        st.session_state.sessions_loaded = True

        # Set current session to most recent or create new one
        if loaded_sessions:
            # Get most recent session
            most_recent_id = sorted(loaded_sessions.keys(), reverse=True)[0]
            st.session_state.current_session_id = most_recent_id
        else:
            # No existing sessions, create first one
            first_session_id = create_new_session(session_service)
            st.session_state.current_session_id = first_session_id


def delete_session_from_ui(session_service: DatabaseSessionService, session_id: str) -> bool:
    """
    Delete a session from both the database and session state.

    Args:
        session_service: The DatabaseSessionService instance
        session_id: The session ID to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        user_id = st.session_state.get("user_id", DEFAULT_USER_ID)

        # Delete from ADK database
        asyncio.run(retry_session_operation(
            session_service.delete_session,
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        ))

        # Remove from session state
        if session_id in st.session_state.sessions:
            del st.session_state.sessions[session_id]

        # If this was the current session, switch to another one
        if st.session_state.current_session_id == session_id:
            remaining_sessions = list(st.session_state.sessions.keys())
            if remaining_sessions:
                # Switch to the most recent session
                st.session_state.current_session_id = sorted(remaining_sessions, reverse=True)[0]
            else:
                # No sessions left, create a new one
                new_session_id = create_new_session(session_service)
                st.session_state.current_session_id = new_session_id

        return True

    except Exception as e:
        st.error(f"Failed to delete session: {e}")
        return False
