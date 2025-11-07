# session_manager.py - Session Memory and Message Management for PostgreSQL

import os
import json
from typing import List, Dict, Any, Optional
from database import get_db_connection, get_placeholder, USE_POSTGRES

# Configuration
MAX_CONTEXT_MESSAGES = int(os.getenv('MAX_CONTEXT_MESSAGES', '10'))


# ===== SESSION DATABASE FUNCTIONS =====

def create_session(session_id: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new conversation session"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        metadata_str = json.dumps(metadata) if metadata else None

        cursor.execute(f"""
            INSERT INTO custom_sessions (session_id, user_id, session_metadata)
            VALUES ({ph}, {ph}, {ph})
        """, (session_id, user_id, metadata_str))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Session {session_id} created successfully",
            "data": {"session_id": session_id, "user_id": user_id}
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating session: {str(e)}",
            "data": None
        }


def save_message(session_id: str, role: str, content: str, token_count: Optional[int] = None) -> Dict[str, Any]:
    """Save a message to session history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        cursor.execute(f"""
            INSERT INTO custom_messages (session_id, role, content, token_count)
            VALUES ({ph}, {ph}, {ph}, {ph})
        """, (session_id, role, content, token_count))

        # Update session last_activity
        cursor.execute(f"""
            UPDATE custom_sessions
            SET last_activity = CURRENT_TIMESTAMP
            WHERE session_id = {ph}
        """, (session_id,))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": "Message saved successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error saving message: {str(e)}"
        }


def load_session_messages(session_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
    """Load conversation history for a session"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        query = f"""
            SELECT message_id, role, content, timestamp, token_count
            FROM custom_messages
            WHERE session_id = {ph}
            ORDER BY timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (session_id,))
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            messages.append({
                "message_id": row[0],
                "role": row[1],
                "content": row[2],
                "timestamp": str(row[3]),
                "token_count": row[4]
            })

        return {
            "status": "success",
            "message": f"Retrieved {len(messages)} messages",
            "data": messages
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error loading session: {str(e)}",
            "data": []
        }


def get_recent_messages(session_id: str, max_messages: int = None) -> List[Dict[str, str]]:
    """Get recent N messages for context window (for ADK callback)"""
    if max_messages is None:
        max_messages = MAX_CONTEXT_MESSAGES

    result = load_session_messages(session_id)

    if result["status"] == "success" and result["data"]:
        messages = result["data"][-max_messages:]
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    return []


def list_sessions(user_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """List all sessions, optionally filtered by user_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        if user_id:
            query = f"""
                SELECT session_id, user_id, created_at, last_activity
                FROM custom_sessions
                WHERE user_id = {ph}
                ORDER BY last_activity DESC
                LIMIT {limit}
            """
            cursor.execute(query, (user_id,))
        else:
            query = f"""
                SELECT session_id, user_id, created_at, last_activity
                FROM custom_sessions
                ORDER BY last_activity DESC
                LIMIT {limit}
            """
            cursor.execute(query)

        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            sessions.append({
                "session_id": row[0],
                "user_id": row[1],
                "created_at": str(row[2]),
                "last_activity": str(row[3])
            })

        return {
            "status": "success",
            "message": f"Retrieved {len(sessions)} sessions",
            "data": sessions
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing sessions: {str(e)}",
            "data": []
        }


def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a session and all its messages"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        # Delete messages first (if CASCADE doesn't work)
        cursor.execute(f"DELETE FROM custom_messages WHERE session_id = {ph}", (session_id,))
        cursor.execute(f"DELETE FROM custom_sessions WHERE session_id = {ph}", (session_id,))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Session {session_id} deleted successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting session: {str(e)}"
        }


# ===== MESSAGE LIMITING AND TOKEN CONTROL =====

def message_limiter(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Callback to limit context window to recent N messages.

    This prevents token overflow while maintaining relevant context.
    Full history is still saved in PostgreSQL.

    Args:
        messages: Full list of conversation messages

    Returns:
        Last N messages to send to LLM
    """
    if len(messages) <= MAX_CONTEXT_MESSAGES:
        return messages

    system_messages = [msg for msg in messages if msg.get('role') == 'system']
    recent_messages = messages[-MAX_CONTEXT_MESSAGES:]

    if system_messages and recent_messages[0].get('role') != 'system':
        return system_messages + recent_messages

    return recent_messages


def save_conversation_turn(session_id: str, user_message: str, assistant_message: str,
                           user_tokens: int = None, assistant_tokens: int = None):
    """
    Save a complete conversation turn (user + assistant) to database.

    Args:
        session_id: Session identifier
        user_message: User's message content
        assistant_message: Assistant's response content
        user_tokens: Optional token count for user message
        assistant_tokens: Optional token count for assistant message
    """
    save_message(session_id, 'user', user_message, user_tokens)
    save_message(session_id, 'assistant', assistant_message, assistant_tokens)


def estimate_tokens(text: str) -> int:
    """Simple token estimation (roughly 4 chars per token)"""
    return len(text) // 4