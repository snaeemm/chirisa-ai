# session_utils.py - Helper functions for ADK session management

import os
import time
import logging
from typing import Optional, Dict, Any
from google.adk.sessions import DatabaseSessionService

DATABASE_URL = os.getenv('DATABASE_URL')


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

async def get_or_create_session(
    session_service: DatabaseSessionService,
    app_name: str,
    user_id: str,
    session_id: Optional[str] = None
) -> str:
    """
    Get existing session or create new one.

    Args:
        session_service: ADK DatabaseSessionService instance
        app_name: Application name (e.g., "data-center-analyzer")
        user_id: User identifier
        session_id: Optional specific session to resume

    Returns:
        session_id: ID of the session to use
    """
    try:
        if session_id:
            # Try to get specific session
            try:
                session = await retry_session_operation(
                    session_service.get_session,
                    app_name=app_name,
                    session_id=session_id
                )
                print(f"📂 Resuming session: {session_id}")
                return session_id
            except:
                print(f"⚠️ Session {session_id} not found, creating new one")

        # Try to get most recent session for this user
        sessions = await retry_session_operation(
            session_service.list_sessions,
            app_name=app_name,
            user_id=user_id
        )

        if sessions.sessions:
            # Use the most recent session
            most_recent = sessions.sessions[0]
            print(f"📂 Continuing existing session: {most_recent.id}")
            return most_recent.id
        else:
            # Create new session
            new_session = await retry_session_operation(
                session_service.create_session,
                app_name=app_name,
                user_id=user_id
            )
            print(f"✨ Created new session: {new_session.id}")
            return new_session.id

    except Exception as e:
        print(f"❌ Error managing session: {e}")
        # Create new session as fallback
        new_session = await retry_session_operation(
            session_service.create_session,
            app_name=app_name,
            user_id=user_id
        )
        return new_session.id


async def list_user_sessions(
    session_service: DatabaseSessionService,
    app_name: str,
    user_id: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    List all sessions for a user.

    Returns:
        Dict with sessions list and metadata
    """
    try:
        sessions = await retry_session_operation(
            session_service.list_sessions,
            app_name=app_name,
            user_id=user_id
        )

        session_list = []
        for session in sessions.sessions[:limit]:
            session_list.append({
                "id": session.id,
                "created_at": str(session.created_at) if hasattr(session, 'created_at') else None,
                "updated_at": str(session.updated_at) if hasattr(session, 'updated_at') else None
            })

        return {
            "status": "success",
            "count": len(session_list),
            "sessions": session_list
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "sessions": []
        }


async def delete_session(
    session_service: DatabaseSessionService,
    app_name: str,
    session_id: str
) -> Dict[str, Any]:
    """Delete a specific session."""
    try:
        await retry_session_operation(
            session_service.delete_session,
            app_name=app_name,
            session_id=session_id
        )
        return {
            "status": "success",
            "message": f"Session {session_id} deleted"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }