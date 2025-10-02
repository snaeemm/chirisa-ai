"""Reports page for viewing datacenter analysis reports."""

import streamlit as st
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from ui.sidebar import render_sidebar
from ui.report_viewer import render_report_viewer

load_dotenv()

st.set_page_config(**PAGE_CONFIG)  # type: ignore[arg-type]

runner, session_service = init_agent()
initialize_sessions(session_service)

with st.sidebar:
    render_sidebar(session_service)

if st.session_state.get("selected_report_id"):
    render_report_viewer(st.session_state.selected_report_id)
else:
    st.info("📊 Select a report from the sidebar to view details.")
