"""All Reports page with map view and summary statistics."""

import streamlit as st
import pandas as pd
import json
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from utils.auth import check_authentication, show_login_form

load_dotenv()

st.set_page_config(**PAGE_CONFIG)

if not check_authentication():
    show_login_form()
    st.stop()

runner, session_service = init_agent()
initialize_sessions(session_service)

with st.sidebar:
    from ui.sidebar import render_sidebar_for_assistant
    render_sidebar_for_assistant(session_service)

st.title("🗺️ All Reports - Global Overview")
st.markdown("---")

try:
    from agent.database import _get_report_summary_rows, get_report_by_id

    reports_result = _get_report_summary_rows(order_clause="created_at DESC")

    if reports_result.get("status") == "success":
        reports = reports_result.get("data", [])

        if not reports:
            st.info("📊 No reports available yet. Start analyzing locations in the Assistant!")
            st.stop()

        total_reports = len(reports)
        avg_score = sum(r.get("composite_score", 0) for r in reports) / total_reports if total_reports > 0 else 0

        excellent = len([r for r in reports if r.get("composite_score", 0) >= 4.0])
        good = len([r for r in reports if 3.0 <= r.get("composite_score", 0) < 4.0])
        fair = len([r for r in reports if 2.0 <= r.get("composite_score", 0) < 3.0])
        poor = len([r for r in reports if r.get("composite_score", 0) < 2.0])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Locations", total_reports, delta=None)

        with col2:
            st.metric("Average Score", f"{avg_score:.2f}", delta=None)

        with col3:
            top_location = max(reports, key=lambda x: x.get("composite_score", 0))
            st.metric("Top Location", top_location.get("location", "N/A")[:20], delta=f"{top_location.get('composite_score', 0):.1f}")

        with col4:
            countries = len(set(r.get("country") for r in reports))
            st.metric("Countries Analyzed", countries, delta=None)

        st.markdown("### 📊 Score Distribution")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background-color: rgba(34, 197, 94, 0.1); border-radius: 0.5rem;'>
                <div style='font-size: 2rem;'>🟢</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{excellent}</div>
                <div style='color: #666;'>Excellent (4.0+)</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background-color: rgba(234, 179, 8, 0.1); border-radius: 0.5rem;'>
                <div style='font-size: 2rem;'>🟡</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{good}</div>
                <div style='color: #666;'>Good (3.0-3.9)</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background-color: rgba(249, 115, 22, 0.1); border-radius: 0.5rem;'>
                <div style='font-size: 2rem;'>🟠</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{fair}</div>
                <div style='color: #666;'>Fair (2.0-2.9)</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background-color: rgba(239, 68, 68, 0.1); border-radius: 0.5rem;'>
                <div style='font-size: 2rem;'>🔴</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{poor}</div>
                <div style='color: #666;'>Poor (<2.0)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🌍 Global Map View")

        map_data = []
        for report in reports:
            report_details = get_report_by_id(report["id"])
            if report_details.get("status") == "success":
                raw_data = report_details["data"].get("raw_data")
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)

                coordinates = raw_data.get("coordinates", {})
                lat = coordinates.get("lat")
                lng = coordinates.get("lng")

                if lat is not None and lng is not None:
                    score = report.get("composite_score", 0)
                    if score >= 4.0:
                        color = [34, 197, 94, 200]
                    elif score >= 3.0:
                        color = [234, 179, 8, 200]
                    elif score >= 2.0:
                        color = [249, 115, 22, 200]
                    else:
                        color = [239, 68, 68, 200]

                    map_data.append({
                        "lat": lat,
                        "lon": lng,
                        "location": report.get("location", "Unknown"),
                        "country": report.get("country", "Unknown"),
                        "score": score,
                        "rating": report.get("rating", "Unknown"),
                        "color": color,
                        "size": 100 + (score * 50)
                    })

        if map_data:
            df = pd.DataFrame(map_data)

            try:
                import pydeck as pdk

                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position=["lon", "lat"],
                    get_color="color",
                    get_radius="size",
                    radius_scale=100,
                    radius_min_pixels=8,
                    radius_max_pixels=40,
                    pickable=True,
                )

                view_state = pdk.ViewState(
                    latitude=df["lat"].mean(),
                    longitude=df["lon"].mean(),
                    zoom=1,
                    pitch=0,
                )

                st.pydeck_chart(pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="light",
                    tooltip={
                        "html": "<b>{location}</b><br/>Country: {country}<br/>Score: {score}<br/>Rating: {rating}",
                        "style": {
                            "backgroundColor": "steelblue",
                            "color": "white",
                            "fontSize": "14px",
                            "padding": "10px"
                        }
                    }
                ))

            except Exception as e:
                st.warning(f"Pydeck not available ({e}), using simple map")
                st.map(df, latitude='lat', longitude='lon', size='size', color='color')

            st.markdown("### 📋 All Locations Summary")

            sorted_reports = sorted(reports, key=lambda x: x.get("composite_score", 0), reverse=True)

            for idx, report in enumerate(sorted_reports, 1):
                score = report.get("composite_score", 0)
                score_emoji = "🟢" if score >= 4.0 else "🟡" if score >= 3.0 else "🟠" if score >= 2.0 else "🔴"

                country_flags = {
                    "Australia": "🇦🇺", "Saudi Arabia": "🇸🇦", "United Arab Emirates": "🇦🇪",
                    "UAE": "🇦🇪", "Canada": "🇨🇦", "France": "🇫🇷", "Grenada": "🇬🇩",
                    "Malaysia": "🇲🇾", "United States": "🇺🇸", "USA": "🇺🇸",
                    "Singapore": "🇸🇬", "Germany": "🇩🇪", "United Kingdom": "🇬🇧", "UK": "🇬🇧",
                    "Japan": "🇯🇵", "South Korea": "🇰🇷", "India": "🇮🇳"
                }
                flag = country_flags.get(report.get("country", ""), "🌍")

                with st.expander(f"#{idx} {score_emoji} {report.get('location', 'Unknown')} - {flag} {report.get('country', 'Unknown')} (Score: {score:.1f})"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown(f"**Score:** {score:.2f}")
                        st.markdown(f"**Rating:** {report.get('rating', 'Unknown')}")

                    with col2:
                        st.markdown(f"**Country:** {report.get('country', 'Unknown')}")
                        st.markdown(f"**Analyzed:** {report.get('created_at', 'N/A')}")

                    with col3:
                        if st.button("📊 View Full Report", key=f"view_{report['id']}"):
                            st.session_state.selected_report_id = report["id"]
                            st.switch_page("pages/Reports.py")

        else:
            st.warning("⚠️ No location coordinates available for mapping. Reports may need to include coordinate data.")

    else:
        st.error(f"Error loading reports: {reports_result.get('message')}")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💬 Go to Assistant", use_container_width=True, type="primary"):
        st.switch_page("Assistant.py")

with col2:
    if st.button("📊 View Individual Reports", use_container_width=True, type="secondary"):
        st.switch_page("pages/Reports.py")

with col3:
    if st.button("🚪 Logout", use_container_width=True):
        from utils.auth import logout
        logout()
