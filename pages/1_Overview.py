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
    from ui.sidebar import render_minimal_sidebar
    render_minimal_sidebar()

st.markdown(
    """
    <style>
    .location-ticker {
        overflow: hidden;
        white-space: nowrap;
        width: 100%;
    }
    .location-ticker-text {
        display: inline-block;
        animation: scroll-location 10s linear infinite;
    }
    @keyframes scroll-location {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .location-ticker:hover .location-ticker-text {
        animation-play-state: paused;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🗺️ Overview")
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
            top_loc_full = top_location.get("location", "N/A")
            top_country = top_location.get("country", "Unknown")

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
            top_flag = country_flags.get(top_country, "🌍")

            top_report_details = get_report_by_id(top_location["id"])
            top_coords_display = "N/A"
            if top_report_details.get("status") == "success":
                raw_data = top_report_details["data"].get("raw_data")
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)
                coords = raw_data.get("coordinates", {})
                top_lat = coords.get("lat")
                top_lng = coords.get("lng")
                if top_lat and top_lng:
                    top_coords_display = f"{top_lat:.2f}, {top_lng:.2f}"

            st.metric("Top Location", f"📍 {top_coords_display}", delta=f"{top_location.get('composite_score', 0):.1f}")

            ticker_content = f"{top_flag} {top_country} • {top_loc_full}"
            if len(ticker_content) > 35:
                st.markdown(
                    f"""
                    <div class='location-ticker' style='margin-top: -0.5rem;'>
                        <span class='location-ticker-text' style='font-size: 0.75rem; color: #666;'>{ticker_content} &nbsp;&nbsp;&nbsp; {ticker_content}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(f"<div style='font-size: 0.75rem; color: #666; margin-top: -0.5rem; text-align: center;'>{ticker_content}</div>", unsafe_allow_html=True)

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

            cols_per_row = 3
            for i in range(0, len(sorted_reports), cols_per_row):
                cols = st.columns(cols_per_row)

                for col_idx, col in enumerate(cols):
                    if i + col_idx < len(sorted_reports):
                        report = sorted_reports[i + col_idx]
                        idx = i + col_idx + 1

                        score = report.get("composite_score", 0)
                        location = report.get("location", "Unknown")
                        country = report.get("country", "Unknown")
                        rating = report.get("rating", "Unknown")
                        created = report.get("created_at", "N/A")

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

                        with col:
                            report_details = get_report_by_id(report["id"])
                            lat, lng = None, None
                            if report_details.get("status") == "success":
                                raw_data = report_details["data"].get("raw_data")
                                if isinstance(raw_data, str):
                                    raw_data = json.loads(raw_data)
                                coords = raw_data.get("coordinates", {})
                                lat = coords.get("lat")
                                lng = coords.get("lng")

                            coords_display = f"({lat:.2f}, {lng:.2f})" if lat and lng else "Coordinates N/A"

                            if len(location) > 25:
                                location_html = f"<div class='location-ticker'><span class='location-ticker-text'>{location} &nbsp;&nbsp;&nbsp; {location}</span></div>"
                            else:
                                location_html = location

                            st.markdown(
                                f"""
                                <div style='padding: 1rem; background-color: rgba(240, 242, 246, 0.5);
                                     border-radius: 0.5rem; border: 2px solid rgba(49, 51, 63, 0.1);
                                     margin-bottom: 1rem; min-height: 220px;'>
                                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;'>
                                        <span style='font-size: 1.5rem; font-weight: bold; color: #666;'>#{idx}</span>
                                        <span style='font-size: 2rem;'>{score_emoji}</span>
                                    </div>
                                    <div style='font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem; min-height: 2.6rem;'>
                                        {location_html}
                                    </div>
                                    <div style='font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;'>
                                        {flag} {country}
                                    </div>
                                    <div style='font-size: 0.8rem; color: #888; margin-bottom: 0.5rem;'>
                                        📍 {coords_display}
                                    </div>
                                    <div style='font-size: 1.5rem; font-weight: bold; color: #ff4b4b; margin: 0.5rem 0;'>
                                        {score:.2f}
                                    </div>
                                    <div style='font-size: 0.85rem; color: #888;'>
                                        {rating} • {created}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            if st.button("📊 View Details", key=f"view_{report['id']}", use_container_width=True, type="secondary"):
                                st.session_state.selected_report_id = report["id"]
                                st.switch_page("pages/3_Reports.py")

        else:
            st.warning("⚠️ No location coordinates available for mapping. Reports may need to include coordinate data.")

    else:
        st.error(f"Error loading reports: {reports_result.get('message')}")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")

