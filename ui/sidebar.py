"""Sidebar UI components for session management and reports."""

import streamlit as st
import sys
import os
from typing import List, Dict, Any, Optional
from google.adk.sessions import DatabaseSessionService

from config.settings import SESSION_CONTAINER_HEIGHT, TITLE_MAX_LENGTH
from services.session_service import create_new_session, delete_session_from_ui

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Center all buttons inside columns
st.markdown("""
<style>
    /* Center all buttons inside columns */
    div[data-testid="stVerticalBlock"] > div > div > button {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

try:
    from agent.database import _get_report_summary_rows, delete_report
except ImportError as e:
    st.error(f"Error importing database functions: {e}")
    _get_report_summary_rows = None
    delete_report = None


@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_reports_list() -> List[Dict[str, Any]]:
    """Load list of all reports from database"""
    if not _get_report_summary_rows:
        return []

    try:
        result = _get_report_summary_rows(order_clause="created_at DESC", limit=50)
        if result.get("status") == "success":
            reports = result.get("data", [])
            # Convert datetime objects to strings for display
            for report in reports:
                if "created_at" in report and hasattr(report["created_at"], "strftime"):
                    report["created_at"] = report["created_at"].strftime("%Y-%m-%d %H:%M")
            return reports
        return []
    except Exception as e:
        st.error(f"Error loading reports: {e}")
        return []


def render_sidebar(session_service: DatabaseSessionService) -> None:
    """
    Render the sidebar with session management and reports controls.

    Args:
        session_service: The DatabaseSessionService instance
    """
    if "selected_report_id" not in st.session_state:
        st.session_state.selected_report_id = None
    if "show_reports" not in st.session_state:
        st.session_state.show_reports = False
    if "show_sessions" not in st.session_state:
        st.session_state.show_sessions = False

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_session_id = create_new_session(session_service)
        st.session_state.current_session_id = new_session_id
        st.session_state.selected_report_id = None
        st.session_state.show_reports = False
        st.switch_page("Assistant.py")

    # Sessions toggle button
    sessions_button_text = "💬 Show Chat Sessions" if not st.session_state.show_sessions else "💬 Hide Chat Sessions"
    if st.button(sessions_button_text, use_container_width=True, type="secondary"):
        st.session_state.show_sessions = not st.session_state.show_sessions
        st.rerun()

    # Show sessions section only if toggled on
    if st.session_state.show_sessions:
        st.markdown("### 💬 Chat Sessions")

        # Calculate container height based on reports visibility
        sessions_height = SESSION_CONTAINER_HEIGHT if not st.session_state.show_reports else int(SESSION_CONTAINER_HEIGHT * 0.6)
        sessions_container = st.container(height=sessions_height)

        with sessions_container:
            for session_id in sorted(st.session_state.sessions.keys(), reverse=True):
                session_data = st.session_state.sessions[session_id]
                is_current = session_id == st.session_state.current_session_id

                # Generate title from first user message or use "New Chat"
                messages = session_data.get("messages", [])
                first_user_msg = next(
                    (
                        m
                        for m in messages
                        if m["role"] == "user" and "content" in m
                    ),
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

                # Create columns for session button and delete button
                if len(st.session_state.sessions) > 1:  # Only show delete if more than 1 session
                    col1, col2 = st.columns([0.85, 0.15])
                else:
                    col1 = st.columns(1)[0]
                    col2 = None

                # Session button
                with col1:
                    if is_current:
                        if st.button(
                            f"📍 {title}",
                            key=f"current_session_{session_id}",
                            use_container_width=True,
                            type="primary",
                        ):
                            st.switch_page("Assistant.py")
                    else:
                        if st.button(
                            title,
                            key=f"session_{session_id}",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state.current_session_id = session_id
                            st.session_state.selected_report_id = None
                            st.switch_page("Assistant.py")

                # Delete button (only show if more than 1 session exists)
                if col2 and len(st.session_state.sessions) > 1:
                    with col2:
                        if st.button(
                            "🗑️",
                            key=f"delete_{session_id}",
                            help="Delete session",
                            use_container_width=True,
                        ):
                            # Confirm deletion
                            if f"confirm_delete_{session_id}" not in st.session_state:
                                st.session_state[f"confirm_delete_{session_id}"] = True
                                st.rerun()
                            else:
                                # Perform deletion
                                if delete_session_from_ui(session_service, session_id):
                                    # Clean up confirmation state
                                    if f"confirm_delete_{session_id}" in st.session_state:
                                        del st.session_state[f"confirm_delete_{session_id}"]
                                    st.rerun()

                # Show confirmation message if deletion was requested
                if f"confirm_delete_{session_id}" in st.session_state:
                    st.warning(f"⚠️ Delete '{title[:20]}...'? Click delete again to confirm.")
                    if st.button("Cancel", key=f"cancel_delete_{session_id}"):
                        del st.session_state[f"confirm_delete_{session_id}"]
                        st.rerun()

    st.divider()

    reports_button_text = "📊 View Reports" if not st.session_state.show_reports else "📊 Hide Reports"
    if st.button(reports_button_text, use_container_width=True, type="secondary"):
        st.session_state.show_reports = not st.session_state.show_reports
        if st.session_state.show_reports:
            load_reports_list.clear()
        st.rerun()

    # Show reports section only if toggled on
    if st.session_state.show_reports:
        st.markdown("### 📊 Reports")

        # Search functionality for reports
        search_term = st.text_input("🔍 Search", placeholder="Location or country...", key="report_search")

        # Load reports
        reports = load_reports_list()

        # Filter reports based on search term
        if search_term:
            filtered_reports = [
                report for report in reports
                if search_term.lower() in report.get("location", "").lower() or
                   search_term.lower() in report.get("country", "").lower()
            ]
        else:
            filtered_reports = reports

        # Compact reports container
        reports_container = st.container(height=int(SESSION_CONTAINER_HEIGHT * 0.4))

        with reports_container:
            if not filtered_reports:
                st.info("No reports found.")
            else:
                for report in filtered_reports:
                    location = report.get("location", "Unknown")
                    country = report.get("country", "Unknown")
                    score = report.get("composite_score", 0)
                    rating = report.get("rating", "Unknown")
                    report_id = report.get("id")
                    analysis_date = report.get("created_at", "")

                    is_current = report_id == st.session_state.selected_report_id

                    # Create compact title for sidebar
                    title = location
                    if len(title) > 20:
                        title = title[:17] + "..."

                    # Score emoji and country flag
                    score_emoji = "🟢" if score >= 4.0 else "🟡" if score >= 3.0 else "🟠" if score >= 2.0 else "🔴"

                    # Country flags
                    country_flags = {
                        "Australia": "🇦🇺", "Saudi Arabia": "🇸🇦", "United Arab Emirates": "🇦🇪",
                        "UAE": "🇦🇪", "Canada": "🇨🇦", "France": "🇫🇷", "Grenada": "🇬🇩",
                        "Malaysia": "🇲🇾", "United States": "🇺🇸", "USA": "🇺🇸"
                    }
                    flag = country_flags.get(country, "🌍")

                    # All reports as buttons with different styling for current
                    if is_current:
                        col1, col2 = st.columns([0.85, 0.15])
                        with col1:
                            if st.button(
                                f"📍 {title}",
                                key=f"current_report_{report_id}",
                                use_container_width=True,
                                type="primary",
                            ):
                                st.switch_page("pages/Reports.py")
                        with col2:
                            if st.button(
                                "🗑️",
                                key=f"delete_current_report_{report_id}",
                                help="Delete report",
                                use_container_width=True,
                            ):
                                if f"confirm_delete_report_{report_id}" not in st.session_state:
                                    st.session_state[f"confirm_delete_report_{report_id}"] = True
                                    st.rerun()
                                else:
                                    if delete_report:
                                        result = delete_report(report_id)
                                        if result.get("status") == "success":
                                            if st.session_state.selected_report_id == report_id:
                                                st.session_state.selected_report_id = None
                                            if f"confirm_delete_report_{report_id}" in st.session_state:
                                                del st.session_state[f"confirm_delete_report_{report_id}"]
                                            load_reports_list.clear()
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to delete: {result.get('message')}")
                        if f"confirm_delete_report_{report_id}" in st.session_state:
                            st.warning(f"⚠️ Delete '{title}'? Click 🗑 again to confirm.")
                            if st.button("Cancel", key=f"cancel_delete_report_{report_id}"):
                                del st.session_state[f"confirm_delete_report_{report_id}"]
                                st.rerun()
                        # Combine metadata in one line for better spacing
                        if analysis_date:
                            st.markdown(f"<small>{flag} {country} • {score_emoji} {score:.1f} • 📅 {analysis_date}</small>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<small>{flag} {country} • {score_emoji} {score:.1f}</small>", unsafe_allow_html=True)
                    else:
                        # Compact report card with delete button
                        col1, col2 = st.columns([0.85, 0.15])

                        with col1:
                            if st.button(
                                f"{title}",
                                key=f"report_{report_id}",
                                use_container_width=True,
                                type="secondary",
                            ):
                                st.session_state.selected_report_id = report_id
                                st.switch_page("pages/Reports.py")

                        with col2:
                            if st.button(
                                "🗑️",
                                key=f"delete_report_{report_id}",
                                help="Delete report",
                                use_container_width=True,
                            ):
                                if f"confirm_delete_report_{report_id}" not in st.session_state:
                                    st.session_state[f"confirm_delete_report_{report_id}"] = True
                                    st.rerun()
                                else:
                                    if delete_report:
                                        result = delete_report(report_id)
                                        if result.get("status") == "success":
                                            if st.session_state.selected_report_id == report_id:
                                                st.session_state.selected_report_id = None
                                            if f"confirm_delete_report_{report_id}" in st.session_state:
                                                del st.session_state[f"confirm_delete_report_{report_id}"]
                                            load_reports_list.clear()
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to delete: {result.get('message')}")

                        # Show confirmation message if deletion was requested
                        if f"confirm_delete_report_{report_id}" in st.session_state:
                            st.warning(f"⚠️ Delete '{title}'? Click 🗑️ again to confirm.")
                            if st.button("Cancel", key=f"cancel_delete_report_{report_id}"):
                                del st.session_state[f"confirm_delete_report_{report_id}"]
                                st.rerun()

                        # Show metadata below button in one compact line
                        if analysis_date:
                            st.markdown(f"<small>{flag} {country} • {score_emoji} {score:.1f} • 📅 {analysis_date}</small>",
                                       unsafe_allow_html=True)
                        else:
                            st.markdown(f"<small>{flag} {country} • {score_emoji} {score:.1f}</small>",
                                       unsafe_allow_html=True)

                        # Add small spacing between reports
                        st.markdown("<br>", unsafe_allow_html=True)

