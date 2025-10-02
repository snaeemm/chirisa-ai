"""Main entry point for the Shahz AI Assistant application."""

import streamlit as st
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from ui.chat_display import render_chat_history
from ui.chat_input import handle_chat_input, check_response_status
from ui.sidebar import render_sidebar

load_dotenv()

st.set_page_config(**PAGE_CONFIG)  # type: ignore[arg-type]

runner, session_service = init_agent()
initialize_sessions(session_service)

with st.sidebar:
    render_sidebar(session_service)

current_session = st.session_state.sessions[st.session_state.current_session_id]

response_status = check_response_status(st.session_state.current_session_id)
if response_status and response_status["status"] == "processing":
    import time
    elapsed = int(time.time() - response_status["start_time"])
    st.info(f"🔄 Agent is working on your request... ({elapsed}s elapsed)")

st.title("💬 Assistant")

render_chat_history(current_session["messages"])

handle_chat_input(current_session, runner)
