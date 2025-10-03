"""Main entry point for the Chirisa AI Assistant application."""

import streamlit as st
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from ui.chat_display import render_chat_history
from ui.chat_input import handle_chat_input, check_response_status
from ui.sidebar import render_sidebar
from utils.auth import check_authentication, show_login_form, logout

load_dotenv()

st.set_page_config(**PAGE_CONFIG)  # type: ignore[arg-type]

if not check_authentication():
    show_login_form()
    st.stop()

runner, session_service = init_agent()
initialize_sessions(session_service)

with st.sidebar:
    from ui.sidebar import render_sidebar_for_assistant
    render_sidebar_for_assistant(session_service)

if not st.session_state.sessions:
    st.info("👋 Welcome! Click 'New Chat' in the sidebar to start a conversation.")
    st.stop()

current_session = st.session_state.sessions.get(st.session_state.current_session_id)
if not current_session:
    st.info("👈 Please select a session from the sidebar or create a new one.")
    st.stop()

response_status = check_response_status(st.session_state.current_session_id)
if response_status and response_status["status"] == "processing":
    import time
    elapsed = int(time.time() - response_status["start_time"])
    st.info(f"🔄 Agent is working on your request... ({elapsed}s elapsed)")

# Title with delete button in top right
col1, col2 = st.columns([0.9, 0.1])
with col1:
    st.title("💬 Assistant")
with col2:
    if len(st.session_state.sessions) > 1:
        if st.button("🗑️", key="delete_current_chat", help="Delete this chat"):
            if "confirm_delete_chat" not in st.session_state:
                st.session_state.confirm_delete_chat = True
                st.rerun()
            else:
                from services.session_service import delete_session_from_ui
                if delete_session_from_ui(session_service, st.session_state.current_session_id):
                    del st.session_state.confirm_delete_chat
                    # Switch to another session
                    remaining_sessions = [sid for sid in st.session_state.sessions.keys() if sid != st.session_state.current_session_id]
                    if remaining_sessions:
                        st.session_state.current_session_id = remaining_sessions[0]
                    st.rerun()

if st.session_state.get("confirm_delete_chat"):
    st.warning("⚠️ Delete this chat? Click 🗑️ again to confirm.")
    if st.button("Cancel", key="cancel_delete_chat"):
        del st.session_state.confirm_delete_chat
        st.rerun()

render_chat_history(current_session["messages"])

handle_chat_input(current_session, runner)
