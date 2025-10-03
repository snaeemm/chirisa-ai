"""Reports page for viewing datacenter analysis reports."""

import streamlit as st
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from ui.sidebar import render_sidebar
from ui.report_viewer import render_report_viewer
from utils.auth import check_authentication, show_login_form, logout

load_dotenv()

st.set_page_config(**PAGE_CONFIG)  # type: ignore[arg-type]

if not check_authentication():
    show_login_form()
    st.stop()

runner, session_service = init_agent()
initialize_sessions(session_service)

with st.sidebar:
    from ui.sidebar import render_sidebar_for_reports
    render_sidebar_for_reports(session_service)

if st.session_state.get("selected_report_id"):
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.title("📊 Report Details")
    with col2:
        if st.button("🗑️", key="delete_current_report", help="Delete this report"):
            if "confirm_delete_report" not in st.session_state:
                st.session_state.confirm_delete_report = True
                st.rerun()
            else:
                from agent.database import delete_report
                from ui.sidebar import load_reports_list
                result = delete_report(st.session_state.selected_report_id)
                if result.get("status") == "success":
                    del st.session_state.confirm_delete_report
                    st.session_state.selected_report_id = None
                    load_reports_list.clear()
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {result.get('message')}")

    if st.session_state.get("confirm_delete_report"):
        st.warning("⚠️ Delete this report? Click 🗑️ again to confirm.")
        if st.button("Cancel", key="cancel_delete_report"):
            del st.session_state.confirm_delete_report
            st.rerun()

    render_report_viewer(st.session_state.selected_report_id)
else:
    st.info("👈 Select a report from the sidebar to view detailed analysis")
