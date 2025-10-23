"""Chat input handling and agent interaction."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING, Any

import streamlit as st
from google.genai import types

from services.document_service import extract_document_text

if TYPE_CHECKING:
    from google.adk.runners import Runner

SessionDict = dict[str, Any]

# Global dictionary to track ongoing responses by session_id
_ongoing_responses: dict[str, dict] = {}


def process_uploaded_files(uploaded_files: list) -> list[dict]:
    """
    Process uploaded files and extract text content.

    Args:
        uploaded_files: List of Streamlit UploadedFile objects

    Returns:
        List of dictionaries with file metadata and extracted text
    """
    processed_files = []

    for uploaded_file in uploaded_files:
        result = extract_document_text(file_object=uploaded_file)

        if result['status'] == 'success':
            st.success(f"✅ {result['filename']}")
            processed_files.append(result)
        else:
            st.error(f"❌ Failed: {result['error']}")

    return processed_files


def start_background_response(session_id: str, user_id: str, prompt_text: str, runner: Runner, uploaded_files: list[dict] | None = None) -> None:
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

            # Create message content with optional file context
            parts = [types.Part(text=prompt_text)]

            # Add extracted text from uploaded files as context
            if uploaded_files:
                for file_data in uploaded_files:
                    file_context = f"[Document: {file_data['filename']}]\n{file_data['text']}"
                    parts.append(types.Part(text=file_context))

            content = types.Content(role="user", parts=parts)

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

    # File upload section
    st.divider()

    # Initialize file uploader counter if not exists (used to reset the uploader)
    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0

    uploaded_files = st.file_uploader(
        "📎 Upload documents (PDF, DOCX, images, etc.)",
        type=["pdf", "docx", "txt", "xlsx", "pptx", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state.file_uploader_key}"
    )

    # Process uploaded files
    if uploaded_files:
        if "processed_files" not in st.session_state:
            st.session_state.processed_files = []

        # Check if new files were added
        current_filenames = {f["filename"] for f in st.session_state.processed_files}
        new_files = [f for f in uploaded_files if f.name not in current_filenames]

        if new_files:
            processed = process_uploaded_files(new_files)
            st.session_state.processed_files.extend(processed)

        # Display uploaded files summary
        if st.session_state.processed_files:
            with st.expander("📄 Uploaded Files", expanded=True):
                for file_data in st.session_state.processed_files:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        file_icon = "📄"
                        if file_data["filename"].endswith((".png", ".jpg", ".jpeg")):
                            file_icon = "🖼️"
                        elif file_data["filename"].endswith(".pdf"):
                            file_icon = "📕"
                        elif file_data["filename"].endswith(".docx"):
                            file_icon = "📗"

                        st.markdown(f"{file_icon} **{file_data['filename']}**")
                        st.caption(f"Type: {file_data.get('document_type', 'Unknown')} | "
                                 f"Size: {len(file_data['text'])} chars")

                    with col2:
                        if st.button("✕", key=f"remove_{file_data['filename']}", use_container_width=True):
                            # Remove from session state (Gemini file already cleaned up during extraction)
                            st.session_state.processed_files.remove(file_data)
                            st.rerun()

    st.divider()

    # Handle new chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Extract text from prompt (handles both string and ChatInputValue)
        prompt_text = prompt if isinstance(prompt, str) else str(prompt)

        # Add user message to chat history
        current_session["messages"].append({"role": "user", "content": prompt_text})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt_text)

        # Get processed files if any
        processed_files = st.session_state.get("processed_files", [])

        # Start background processing
        start_background_response(
            session_id=session_id,
            user_id=st.session_state.user_id,
            prompt_text=prompt_text,
            runner=runner,
            uploaded_files=processed_files if processed_files else None
        )

        # Clear uploaded files after message is sent
        st.session_state.processed_files = []
        # Reset file uploader widget by changing its key
        st.session_state.file_uploader_key += 1

        # Show immediate feedback and refresh
        st.info("🚀 Processing your request... (continues in background)")
        st.rerun()
