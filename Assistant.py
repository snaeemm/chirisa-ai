"""Main entry point for the Shahz AI Assistant application."""

import streamlit as st
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from ui.chat_display import render_chat_history
from ui.chat_input import handle_chat_input, check_response_status
from ui.sidebar import render_sidebar
from ui.report_viewer import render_report_viewer

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(**PAGE_CONFIG)  # type: ignore[arg-type]

# Initialize ADK components
runner, session_service = init_agent()

# Initialize/load sessions
initialize_sessions(session_service)

# Render sidebar
with st.sidebar:
    render_sidebar(session_service)

# Initialize view mode if not set
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "chat"

# Main content area - switch between chat and report view
if st.session_state.view_mode == "report" and st.session_state.get("selected_report_id"):
    # Report view mode
    render_report_viewer(st.session_state.selected_report_id)
else:
    # Chat view mode
    # Get current session data
    current_session = st.session_state.sessions[st.session_state.current_session_id]

    # Check for ongoing responses and show status
    response_status = check_response_status(st.session_state.current_session_id)
    if response_status and response_status["status"] == "processing":
        import time
        elapsed = int(time.time() - response_status["start_time"])
        st.info(f"🔄 Agent is working on your request... ({elapsed}s elapsed)")

    # Main chat area
    st.title("💬 Assistant")

    # Display chat history
    render_chat_history(current_session["messages"])

    # Handle chat input
    handle_chat_input(current_session, runner)
