"""Chat input handling and agent interaction."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING, Any

import streamlit as st
from google.genai import types

if TYPE_CHECKING:
    from google.adk.runners import Runner

SessionDict = dict[str, Any]

# Global dictionary to track ongoing responses by session_id
_ongoing_responses: dict[str, dict] = {}


def start_background_response(session_id: str, user_id: str, prompt_text: str, runner: Runner) -> None:
    """Start agent response processing in background thread."""
    async def process_response():
        try:
            # Initialize response tracking
            response_data = {
                "status": "processing",
                "messages": [],
                "final_response": None,
                "error": None,
                "start_time": time.time()
            }
            _ongoing_responses[session_id] = response_data

            # Create message content
            content = types.Content(
                role="user", parts=[types.Part(text=prompt_text)]
            )

            # Process agent response
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                # Store tool calls and responses
                if event.get_function_calls():
                    for func_call in event.get_function_calls():
                        response_data["messages"].append({
                            "role": "assistant",
                            "type": "tool_call",
                            "tool_name": func_call.name,
                            "args": func_call.args,
                        })

                if event.get_function_responses():
                    for func_response in event.get_function_responses():
                        response_data["messages"].append({
                            "role": "assistant",
                            "type": "tool_response",
                            "tool_name": func_response.name,
                            "response": func_response.response,
                        })

                # Check for final response
                final_response = _check_final_response(event)
                if final_response:
                    response_data["final_response"] = final_response
                    response_data["status"] = "completed"
                    break

            # Mark as completed if no final response
            if response_data["status"] == "processing":
                response_data["status"] = "completed"

        except Exception as e:
            _ongoing_responses[session_id] = {
                "status": "error",
                "error": str(e),
                "messages": [],
                "final_response": None
            }

    # Run in background thread
    def run_async():
        asyncio.run(process_response())

    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()


def check_response_status(session_id: str) -> dict | None:
    """Check if there's an ongoing or completed response for a session."""
    return _ongoing_responses.get(session_id)


def cleanup_completed_response(session_id: str) -> None:
    """Remove completed response from tracking."""
    if session_id in _ongoing_responses:
        del _ongoing_responses[session_id]


def _process_tool_calls(event: Any, current_session: SessionDict) -> None:
    """Process and display tool calls from event."""
    if not (event.content and event.get_function_calls()):
        return

    for func_call in event.get_function_calls():
        # Display tool call
        with st.expander(f"🔧 Tool Call: {func_call.name}", expanded=False):
            st.json(func_call.args)

        # Save to history
        current_session["messages"].append({
            "role": "assistant",
            "type": "tool_call",
            "tool_name": func_call.name,
            "args": func_call.args,
        })


def _process_tool_responses(event: Any, current_session: SessionDict) -> None:
    """Process and display tool responses from event."""
    if not (event.content and event.get_function_responses()):
        return

    for func_response in event.get_function_responses():
        # Display tool response
        with st.expander(f"✅ Tool Response: {func_response.name}", expanded=False):
            st.json(func_response.response)

        # Save to history
        current_session["messages"].append({
            "role": "assistant",
            "type": "tool_response",
            "tool_name": func_response.name,
            "response": func_response.response,
        })


def _check_final_response(event: Any) -> str | None:
    """Check if event contains final response and return it."""
    if (
        event.is_final_response()
        and event.content
        and event.content.parts
        and len(event.content.parts) > 0
        and event.content.parts[0].text
    ):
        return event.content.parts[0].text
    return None


def handle_chat_input(current_session: SessionDict, runner: Runner) -> None:
    """
    Handle user chat input and agent response with session persistence.

    Args:
        current_session: Current session dictionary
        runner: The ADK Runner instance
    """
    session_id = st.session_state.current_session_id

    # Check for ongoing or completed responses first
    response_status = check_response_status(session_id)
    if response_status:
        if response_status["status"] == "processing":
            # Show processing status and auto-refresh
            elapsed = int(time.time() - response_status["start_time"])
            st.info(f"🔄 Processing your request... ({elapsed}s elapsed, continues in background)")
            time.sleep(2)  # Wait 2 seconds before refresh
            st.rerun()

        elif response_status["status"] == "completed":
            # Display completed response
            with st.chat_message("assistant"):
                st.success("✅ Response ready!")

                # Add all stored messages to session
                for msg in response_status["messages"]:
                    current_session["messages"].append(msg)

                # Display final response
                if response_status["final_response"]:
                    st.markdown(response_status["final_response"])
                    current_session["messages"].append({
                        "role": "assistant",
                        "content": response_status["final_response"],
                    })

            # Clean up completed response
            cleanup_completed_response(session_id)
            st.rerun()

        elif response_status["status"] == "error":
            st.error(f"❌ Error processing request: {response_status['error']}")
            cleanup_completed_response(session_id)

    # Handle new chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Extract text from prompt (handles both string and ChatInputValue)
        prompt_text = prompt if isinstance(prompt, str) else str(prompt)

        # Add user message to chat history
        current_session["messages"].append({"role": "user", "content": prompt_text})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt_text)

        # Start background processing
        start_background_response(
            session_id=session_id,
            user_id=st.session_state.user_id,
            prompt_text=prompt_text,
            runner=runner
        )

        # Show immediate feedback and refresh
        st.info("🚀 Processing your request... (continues in background)")
        st.rerun()
