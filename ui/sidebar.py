"""Sidebar UI components for session management and reports."""

import streamlit as st
import sys
import os
from typing import List, Dict, Any
from google.adk.sessions import DatabaseSessionService

from config.settings import TITLE_MAX_LENGTH
from services.session_service import create_new_session, delete_session_from_ui

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    from agent.database import _get_report_summary_rows, delete_report
except ImportError as e:
    st.error(f"Error importing database functions: {e}")
    _get_report_summary_rows = None
    delete_report = None


@st.cache_data(ttl=30)
def load_reports_list() -> List[Dict[str, Any]]:
    """Load list of all reports from database"""
    if not _get_report_summary_rows:
        return []

    try:
        result = _get_report_summary_rows(order_clause="created_at DESC", limit=50)
        if result.get("status") == "success":
            reports = result.get("data", [])
            for report in reports:
                if "created_at" in report and hasattr(report["created_at"], "strftime"):
                    report["created_at"] = report["created_at"].strftime("%Y-%m-%d %H:%M")
            return reports
        return []
    except Exception as e:
        st.error(f"Error loading reports: {e}")
        return []


def render_sidebar_for_assistant(session_service: DatabaseSessionService) -> None:
    """Render sidebar for Assistant page with sessions list."""

    st.markdown(
        """
        <style>
        .session-item {
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 0.5rem;
            cursor: pointer;
        }
        .session-item-current {
            background-color: rgba(255, 75, 75, 0.1);
            border-left: 3px solid #ff4b4b;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_session_id = create_new_session(session_service)
        st.session_state.current_session_id = new_session_id
        st.rerun()

    st.markdown("---")
    st.markdown("### 💬 Chat Sessions")

    sessions_container = st.container(height=500)

    with sessions_container:
        if not st.session_state.sessions:
            st.info("No chat sessions yet. Click 'New Chat' to start!")
        else:
            for session_id in sorted(st.session_state.sessions.keys(), reverse=True):
                session_data = st.session_state.sessions[session_id]
                is_current = session_id == st.session_state.current_session_id

                messages = session_data.get("messages", [])
                first_user_msg = next(
                    (m for m in messages if m["role"] == "user" and "content" in m),
                    None,
                )

                if first_user_msg:
                    content = first_user_msg["content"]
                    title = (
                        content[:TITLE_MAX_LENGTH] + "..."
                        if len(content) > TITLE_MAX_LENGTH
                        else content
                    )
                else:
                    title = "New Chat"

                if is_current:
                    st.button(
                        f"📍 {title}",
                        key=f"current_session_{session_id}",
                        use_container_width=True,
                        type="primary",
                        disabled=True
                    )
                else:
                    if st.button(
                        title,
                        key=f"session_{session_id}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state.current_session_id = session_id
                        st.rerun()

    st.markdown("---")

    if st.button("🗺️ All Reports Map", use_container_width=True, type="secondary"):
        st.switch_page("pages/All_Reports.py")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True, key="logout_assistant"):
        from utils.auth import logout
        logout()


def render_sidebar_for_reports(session_service: DatabaseSessionService) -> None:
    """Render sidebar for Reports page with reports list."""

    if "selected_report_id" not in st.session_state:
        st.session_state.selected_report_id = None

    st.markdown(
        """
        <style>
        .report-card {
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 0.5rem;
            background-color: rgba(240, 242, 246, 0.5);
            border: 1px solid rgba(49, 51, 63, 0.1);
        }
        .report-card-selected {
            background-color: rgba(255, 75, 75, 0.1);
            border-left: 3px solid #ff4b4b;
        }
        .report-title {
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 0.25rem;
        }
        .report-meta {
            font-size: 0.8rem;
            color: #666;
            line-height: 1.4;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_session_id = create_new_session(session_service)
        st.session_state.current_session_id = new_session_id
        st.switch_page("Assistant.py")

    st.markdown("---")
    st.markdown("### 📊 Reports")

    search_term = st.text_input("🔍 Search", placeholder="Location or country...", key="report_search")

    reports = load_reports_list()

    if search_term:
        filtered_reports = [
            report for report in reports
            if search_term.lower() in report.get("location", "").lower() or
               search_term.lower() in report.get("country", "").lower()
        ]
    else:
        filtered_reports = reports

    reports_container = st.container(height=400)

    with reports_container:
        if not filtered_reports:
            st.info("No reports found." if search_term else "No reports available yet.")
        else:
            for report in filtered_reports:
                location = report.get("location", "Unknown")
                country = report.get("country", "Unknown")
                score = report.get("composite_score", 0)
                rating = report.get("rating", "Unknown")
                report_id = report.get("id")
                analysis_date = report.get("created_at", "")

                is_current = report_id == st.session_state.selected_report_id

                display_title = location if len(location) <= 25 else location[:22] + "..."

                score_emoji = "🟢" if score >= 4.0 else "🟡" if score >= 3.0 else "🟠" if score >= 2.0 else "🔴"

                country_flags = {
                    "Australia": "🇦🇺", "Saudi Arabia": "🇸🇦", "United Arab Emirates": "🇦🇪",
                    "UAE": "🇦🇪", "Canada": "🇨🇦", "France": "🇫🇷", "Grenada": "🇬🇩",
                    "Malaysia": "🇲🇾", "United States": "🇺🇸", "USA": "🇺🇸"
                }
                flag = country_flags.get(country, "🌍")

                col1, col2 = st.columns([0.85, 0.15])

                with col1:
                    if is_current:
                        st.button(
                            f"📍 {display_title}",
                            key=f"current_report_{report_id}",
                            use_container_width=True,
                            type="primary",
                            disabled=True
                        )
                    else:
                        if st.button(
                            display_title,
                            key=f"report_{report_id}",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state.selected_report_id = report_id
                            st.rerun()

                with col2:
                    st.markdown(f"<div style='text-align: center; font-size: 1.2rem; margin-top: 0.25rem;'>{score_emoji}</div>", unsafe_allow_html=True)

                st.markdown(
                    f"<div class='report-meta'>{flag} {country} • Score: {score:.1f}<br/>📅 {analysis_date}</div>",
                    unsafe_allow_html=True
                )
                st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🗺️ All Reports Map", use_container_width=True, type="secondary", key="map_from_reports"):
        st.switch_page("pages/All_Reports.py")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True, key="logout_reports"):
        from utils.auth import logout
        logout()


def render_sidebar(session_service: DatabaseSessionService) -> None:
    """Legacy wrapper for backward compatibility - not used in new design."""
    current_page = st.session_state.get("page", "Assistant")

    if current_page == "Reports" or "Reports" in str(st.runtime.scriptrunner.get_script_run_ctx().page_script_hash):
        render_sidebar_for_reports(session_service)
    else:
        render_sidebar_for_assistant(session_service)
