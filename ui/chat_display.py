"""Chat display UI components."""

from __future__ import annotations

from typing import Any

import streamlit as st

MessageDict = dict[str, Any]


def render_message(message: MessageDict) -> None:
    """
    Render a single message in the chat.

    Args:
        message: Message dictionary with role, content, and optional type/tool info
    """
    with st.chat_message(message["role"]):
        if message.get("type") == "tool_call":
            # Display tool call in an expander
            with st.expander(
                f"🔧 Tool Call: {message['tool_name']}", expanded=False
            ):
                st.json(message["args"])
        elif message.get("type") == "tool_response":
            # Display tool response in an expander
            with st.expander(
                f"✅ Tool Response: {message['tool_name']}", expanded=False
            ):
                st.json(message["response"])
        else:
            # Regular text message
            st.markdown(message["content"])


def render_chat_history(messages: list[MessageDict]) -> None:
    """
    Render all messages in the chat history.

    Args:
        messages: List of message dictionaries
    """
    for message in messages:
        render_message(message)
