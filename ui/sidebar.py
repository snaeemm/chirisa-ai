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
    """Load list of all reports from database with coordinates"""
    if not _get_report_summary_rows:
        return []

    try:
        from agent.database import get_report_by_id
        import json

        result = _get_report_summary_rows(order_clause="created_at DESC", limit=50)
        if result.get("status") == "success":
            reports = result.get("data", [])
            for report in reports:
                if "created_at" in report and hasattr(report["created_at"], "strftime"):
                    report["created_at"] = report["created_at"].strftime("%Y-%m-%d %H:%M")

                report_details = get_report_by_id(report["id"])
                if report_details.get("status") == "success":
                    raw_data = report_details["data"].get("raw_data")
                    if isinstance(raw_data, str):
                        raw_data = json.loads(raw_data)
                    coords = raw_data.get("coordinates", {})
                    report["lat"] = coords.get("lat")
                    report["lng"] = coords.get("lng")
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
        .session-ticker {
            overflow: hidden;
            white-space: nowrap;
            width: 100%;
        }
        .session-ticker-text {
            display: inline-block;
            animation: session-scroll 8s linear infinite;
        }
        @keyframes session-scroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        .session-ticker:hover .session-ticker-text {
            animation-play-state: paused;
        }
        /* Make button text scroll on hover */
        button[data-testid="baseButton-secondary"] p,
        button[data-testid="baseButton-primary"] p {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            transition: transform 0.3s ease;
        }
        button[data-testid="baseButton-secondary"]:hover p,
        button[data-testid="baseButton-primary"]:hover p {
            animation: button-scroll 3s linear infinite;
        }
        @keyframes button-scroll {
            0%, 10% { transform: translateX(0); }
            90%, 100% { transform: translateX(calc(-100% + 100px)); }
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
                    full_title = content
                else:
                    full_title = "New Chat"

                # Button with full text - will scroll on hover via CSS
                if is_current:
                    st.button(
                        f"📍 {full_title}",
                        key=f"current_session_{session_id}",
                        use_container_width=True,
                        type="primary",
                        disabled=True
                    )
                else:
                    if st.button(
                        full_title,
                        key=f"session_{session_id}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state.current_session_id = session_id
                        st.rerun()

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
        .ticker-container {
            overflow: hidden;
            white-space: nowrap;
            width: 100%;
        }
        .ticker-text {
            display: inline-block;
            padding-left: 100%;
            animation: ticker 12s linear infinite;
        }
        @keyframes ticker {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-100%, 0); }
        }
        .ticker-text:hover {
            animation-play-state: paused;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

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
                report_id = report.get("id")
                lat = report.get("lat")
                lng = report.get("lng")

                is_current = report_id == st.session_state.selected_report_id

                score_emoji = "🟢" if score >= 4.0 else "🟡" if score >= 3.0 else "🟠" if score >= 2.0 else "🔴"

                country_flags = {
                    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Andorra": "🇦🇩", "Angola": "🇦🇴",
                    "Argentina": "🇦🇷", "Armenia": "🇦🇲", "Australia": "🇦🇺", "Austria": "🇦🇹", "Azerbaijan": "🇦🇿",
                    "Bahamas": "🇧🇸", "Bahrain": "🇧🇭", "Bangladesh": "🇧🇩", "Barbados": "🇧🇧", "Belarus": "🇧🇾",
                    "Belgium": "🇧🇪", "Belize": "🇧🇿", "Benin": "🇧🇯", "Bhutan": "🇧🇹", "Bolivia": "🇧🇴",
                    "Bosnia": "🇧🇦", "Botswana": "🇧🇼", "Brazil": "🇧🇷", "Brunei": "🇧🇳", "Bulgaria": "🇧🇬",
                    "Burkina Faso": "🇧🇫", "Burundi": "🇧🇮", "Cambodia": "🇰🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦",
                    "Cape Verde": "🇨🇻", "Chad": "🇹🇩", "Chile": "🇨🇱", "China": "🇨🇳", "Colombia": "🇨🇴",
                    "Costa Rica": "🇨🇷", "Croatia": "🇭🇷", "Cuba": "🇨🇺", "Cyprus": "🇨🇾", "Czech Republic": "🇨🇿",
                    "Denmark": "🇩🇰", "Djibouti": "🇩🇯", "Dominican Republic": "🇩🇴", "Ecuador": "🇪🇨", "Egypt": "🇪🇬",
                    "El Salvador": "🇸🇻", "Estonia": "🇪🇪", "Ethiopia": "🇪🇹", "Fiji": "🇫🇯", "Finland": "🇫🇮",
                    "France": "🇫🇷", "Gabon": "🇬🇦", "Gambia": "🇬🇲", "Georgia": "🇬🇪", "Germany": "🇩🇪",
                    "Ghana": "🇬🇭", "Greece": "🇬🇷", "Grenada": "🇬🇩", "Guatemala": "🇬🇹", "Guinea": "🇬🇳",
                    "Guyana": "🇬🇾", "Haiti": "🇭🇹", "Honduras": "🇭🇳", "Hungary": "🇭🇺", "Iceland": "🇮🇸",
                    "India": "🇮🇳", "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ireland": "🇮🇪",
                    "Israel": "🇮🇱", "Italy": "🇮🇹", "Jamaica": "🇯🇲", "Japan": "🇯🇵", "Jordan": "🇯🇴",
                    "Kazakhstan": "🇰🇿", "Kenya": "🇰🇪", "Kuwait": "🇰🇼", "Kyrgyzstan": "🇰🇬", "Laos": "🇱🇦",
                    "Latvia": "🇱🇻", "Lebanon": "🇱🇧", "Liberia": "🇱🇷", "Libya": "🇱🇾", "Lithuania": "🇱🇹",
                    "Luxembourg": "🇱🇺", "Madagascar": "🇲🇬", "Malaysia": "🇲🇾", "Maldives": "🇲🇻", "Mali": "🇲🇱",
                    "Malta": "🇲🇹", "Mauritius": "🇲🇺", "Mexico": "🇲🇽", "Moldova": "🇲🇩", "Monaco": "🇲🇨",
                    "Mongolia": "🇲🇳", "Montenegro": "🇲🇪", "Morocco": "🇲🇦", "Mozambique": "🇲🇿", "Myanmar": "🇲🇲",
                    "Namibia": "🇳🇦", "Nepal": "🇳🇵", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿", "Nicaragua": "🇳🇮",
                    "Niger": "🇳🇪", "Nigeria": "🇳🇬", "North Korea": "🇰🇵", "Norway": "🇳🇴", "Oman": "🇴🇲",
                    "Pakistan": "🇵🇰", "Panama": "🇵🇦", "Paraguay": "🇵🇾", "Peru": "🇵🇪", "Philippines": "🇵🇭",
                    "Poland": "🇵🇱", "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Romania": "🇷🇴", "Russia": "🇷🇺",
                    "Rwanda": "🇷🇼", "Saudi Arabia": "🇸🇦", "Senegal": "🇸🇳", "Serbia": "🇷🇸", "Singapore": "🇸🇬",
                    "Slovakia": "🇸🇰", "Slovenia": "🇸🇮", "Somalia": "🇸🇴", "South Africa": "🇿🇦", "South Korea": "🇰🇷",
                    "South Sudan": "🇸🇸", "Spain": "🇪🇸", "Sri Lanka": "🇱🇰", "Sudan": "🇸🇩", "Sweden": "🇸🇪",
                    "Switzerland": "🇨🇭", "Syria": "🇸🇾", "Taiwan": "🇹🇼", "Tajikistan": "🇹🇯", "Tanzania": "🇹🇿",
                    "Thailand": "🇹🇭", "Tunisia": "🇹🇳", "Turkey": "🇹🇷", "Turkmenistan": "🇹🇲", "Uganda": "🇺🇬",
                    "Ukraine": "🇺🇦", "United Arab Emirates": "🇦🇪", "UAE": "🇦🇪", "United Kingdom": "🇬🇧", "UK": "🇬🇧",
                    "United States": "🇺🇸", "USA": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿", "Venezuela": "🇻🇪",
                    "Vietnam": "🇻🇳", "Yemen": "🇾🇪", "Zambia": "🇿🇲", "Zimbabwe": "🇿🇼"
                }
                flag = country_flags.get(country, "🌍")

                coords_display = f"({lat:.2f}, {lng:.2f})" if lat and lng else "No coords"

                button_text = f"{score_emoji} {flag} {country}\n📍 {coords_display} • {score:.1f}"

                if is_current:
                    st.button(
                        button_text,
                        key=f"current_report_{report_id}",
                        use_container_width=True,
                        type="primary",
                        disabled=True
                    )
                else:
                    if st.button(
                        button_text,
                        key=f"report_{report_id}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state.selected_report_id = report_id
                        st.rerun()

                if len(location) > 25:
                    st.markdown(
                        f"""
                        <div class='ticker-container' style='font-size: 0.7rem; margin-top: -0.75rem; margin-bottom: 0.75rem;'>
                            <span class='ticker-text'>{location} &nbsp;&nbsp;&nbsp; {location}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div style='font-size: 0.7rem; color: #666; margin-top: -0.75rem; margin-bottom: 0.75rem; text-align: center;'>
                            {location}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True, key="logout_reports"):
        from utils.auth import logout
        logout()


def render_minimal_sidebar() -> None:
    """Render minimal sidebar with just logout button."""

    if st.button("🚪 Logout", use_container_width=True):
        from utils.auth import logout
        logout()


def render_sidebar(session_service: DatabaseSessionService) -> None:
    """Legacy wrapper for backward compatibility - not used in new design."""
    current_page = st.session_state.get("page", "Assistant")

    if current_page == "Reports" or "Reports" in str(st.runtime.scriptrunner.get_script_run_ctx().page_script_hash):
        render_sidebar_for_reports(session_service)
    else:
        render_sidebar_for_assistant(session_service)
