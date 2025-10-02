"""Report viewer UI component for displaying datacenter analysis reports."""

import streamlit as st
import pandas as pd
import json
import sys
import os
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent.database import get_report_by_id
except ImportError as e:
    st.error(f"Error importing database functions: {e}")
    get_report_by_id = None

# Custom CSS for better styling
REPORT_CSS = """
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.score-excellent { color: #28a745; }
.score-good { color: #17a2b8; }
.score-moderate { color: #ffc107; }
.score-poor { color: #dc3545; }
.domain-score {
    font-size: 1.2rem;
    font-weight: bold;
}
</style>
"""

def get_rating_color(rating: str) -> str:
    """Get color class for rating"""
    rating_colors = {
        "Excellent": "score-excellent",
        "Good": "score-good",
        "Moderate": "score-moderate",
        "Poor": "score-poor"
    }
    return rating_colors.get(rating, "")

def get_score_color(score: float) -> str:
    """Get color class for score"""
    if score >= 4.0:
        return "score-excellent"
    elif score >= 3.0:
        return "score-good"
    elif score >= 2.0:
        return "score-moderate"
    else:
        return "score-poor"

@st.cache_data(ttl=300)
def load_report_details(report_id: int) -> Optional[Dict[str, Any]]:
    """Load detailed report data by ID"""
    if not get_report_by_id:
        return None

    try:
        result = get_report_by_id(report_id)
        if result.get("status") == "success":
            return result.get("data")
        else:
            st.error(f"Error loading report: {result.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Error loading report details: {e}")
        return None

def render_metrics_table(metrics: Dict[str, Any], section_name: str):
    """Render metrics data as comprehensive tables"""
    if not metrics:
        return

    # Create tabs for different metric types
    tabs_to_create = []
    tab_data = []

    # Numerical values table
    if metrics.get("numerical_values"):
        numerical_data = []
        units = metrics.get("units", {})
        for key, value in metrics["numerical_values"].items():
            unit = units.get(key, "")
            # Format value based on type
            if isinstance(value, float):
                formatted_value = f"{value:.2f}" if value != int(value) else f"{int(value)}"
            else:
                formatted_value = str(value)

            numerical_data.append({
                "Metric": key.replace("_", " ").title(),
                "Value": formatted_value,
                "Unit": unit
            })
        if numerical_data:
            tabs_to_create.append("📊 Numerical")
            tab_data.append(("numerical", pd.DataFrame(numerical_data)))

    # Percentages table
    if metrics.get("percentages"):
        percentage_data = []
        for key, value in metrics["percentages"].items():
            formatted_value = f"{value:.1f}%" if isinstance(value, float) else f"{value}%"
            percentage_data.append({
                "Metric": key.replace("_", " ").title(),
                "Percentage": formatted_value
            })
        if percentage_data:
            tabs_to_create.append("📈 Percentages")
            tab_data.append(("percentage", pd.DataFrame(percentage_data)))

    # Ranges table
    if metrics.get("ranges"):
        range_data = []
        units = metrics.get("units", {})
        for key, value in metrics["ranges"].items():
            if isinstance(value, dict) and "min" in value and "max" in value:
                unit = units.get(key, "")
                min_val = f"{value['min']:.2f}" if isinstance(value['min'], float) else str(value['min'])
                max_val = f"{value['max']:.2f}" if isinstance(value['max'], float) else str(value['max'])
                range_data.append({
                    "Metric": key.replace("_", " ").title(),
                    "Min": min_val,
                    "Max": max_val,
                    "Unit": unit
                })
        if range_data:
            tabs_to_create.append("📏 Ranges")
            tab_data.append(("range", pd.DataFrame(range_data)))

    # Only render if we have data
    if tabs_to_create:
        # Create tabs for different metric types
        if len(tabs_to_create) > 1:
            tabs = st.tabs(tabs_to_create)
            for i, (tab_type, df) in enumerate(tab_data):
                with tabs[i]:
                    st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            # Single table, no tabs needed
            _, df = tab_data[0]
            st.dataframe(df, use_container_width=True, hide_index=True)

def render_domain_analysis(domain_name: str, domain_data: Dict[str, Any], structured_analysis: Dict[str, Any]):
    """Render a single domain analysis section with complete detailed analysis"""
    score = domain_data.get("score", 0)
    summary = domain_data.get("summary", "")
    key_findings = domain_data.get("key_findings", [])

    # Get structured analysis for this domain
    domain_structured = structured_analysis.get(domain_name, {})

    with st.expander(f"🔍 {domain_name.replace('_', ' ').title()}", expanded=False):
        # Score display and summary
        col1, col2 = st.columns([1, 3])
        with col1:
            score_color = get_score_color(score)
            st.markdown(f'<div class="domain-score {score_color}">{score:.1f}/5.0</div>',
                       unsafe_allow_html=True)

            # Progress bar
            progress_color = "🟢" if score >= 4.0 else "🟡" if score >= 3.0 else "🟠" if score >= 2.0 else "🔴"
            st.progress(score / 5.0)
            st.write(f"{progress_color} Score: {score:.1f}/5.0")

        with col2:
            if summary:
                st.write("**Summary:**")
                st.write(summary)

        # Key findings
        if key_findings:
            st.write("**Key Findings:**")
            for finding in key_findings:
                st.write(f"• {finding}")

        st.divider()

        # Render detailed structured analysis sections
        if domain_structured and isinstance(domain_structured, dict):
            st.write("**📊 Detailed Analysis Sections:**")

            # Iterate through all subsections in this domain
            for section_key, section_data in domain_structured.items():
                if isinstance(section_data, dict):
                    # Skip non-section data like assumptions and overall metrics
                    if section_key in ['assumptions', 'overall_score', 'phase_1_deployment', 'phase_1_recommendations']:
                        continue

                    section_name = section_data.get("name", section_key.replace("_", " ").title())
                    content = section_data.get("content", "")
                    sub_score = section_data.get("sub_score", -1)
                    metrics = section_data.get("metrics", {})
                    key_points = section_data.get("key_points", [])

                    # Create a nested expander for each subsection
                    with st.expander(f"📋 {section_name}", expanded=False):
                        # Sub-score display
                        if sub_score > 0:
                            sub_score_color = get_score_color(sub_score)
                            st.markdown(f'<div class="metric-card"><strong>Sub-score:</strong> <span class="{sub_score_color}">{sub_score:.1f}/5.0</span></div>',
                                       unsafe_allow_html=True)

                        # Content
                        if content:
                            st.write("**Analysis:**")
                            st.write(content)

                        # Key points
                        if key_points:
                            st.write("**Key Points:**")
                            for point in key_points:
                                st.write(f"• {point}")

                        # Render metrics tables if available
                        if metrics and any(metrics.get(key, {}) for key in ['numerical_values', 'percentages', 'ranges']):
                            st.write("**📊 Metrics & Data:**")
                            render_metrics_table(metrics, section_name)

        # Show assumptions if available
        if domain_structured and 'assumptions' in domain_structured:
            assumptions = domain_structured['assumptions']
            if assumptions and isinstance(assumptions, list):
                st.write("**📝 Assumptions:**")
                for assumption in assumptions:
                    st.write(f"• {assumption}")

def render_report_viewer(report_id: int):
    """Render the complete report viewer for a given report ID"""
    # Load report data
    report_data = load_report_details(report_id)

    if not report_data:
        st.error("Could not load report data.")
        return

    # Add custom CSS
    st.markdown(REPORT_CSS, unsafe_allow_html=True)

    raw_data = report_data.get("raw_data", {})

    # Header section
    location_name = raw_data.get('location', 'Unknown Location')
    country = raw_data.get("country", "Unknown")

    # Title with country flag emoji (basic mapping)
    country_flags = {
        "Australia": "🇦🇺", "Saudi Arabia": "🇸🇦", "United Arab Emirates": "🇦🇪",
        "UAE": "🇦🇪", "Canada": "🇨🇦", "France": "🇫🇷", "Grenada": "🇬🇩",
        "Malaysia": "🇲🇾", "United States": "🇺🇸", "USA": "🇺🇸"
    }
    flag = country_flags.get(country, "🌍")

    st.title(f"{flag} {location_name}")
    st.caption(f"Comprehensive datacenter site analysis for {country}")

    # Overall metrics with enhanced styling
    overall_suitability = raw_data.get("overall_suitability", {})
    composite_score = overall_suitability.get("composite_score", 0)
    rating = overall_suitability.get("rating", "Unknown")
    recommendation = overall_suitability.get("recommendation", "")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        score_color = get_score_color(composite_score)
        progress_val = composite_score / 5.0 if composite_score > 0 else 0
        st.markdown(f'<div class="metric-card"><strong>Overall Score</strong><br>'
                   f'<span class="domain-score {score_color}">{composite_score:.1f}/5.0</span></div>',
                   unsafe_allow_html=True)
        st.progress(progress_val)

    with col2:
        rating_color = get_rating_color(rating)
        rating_icon = {"Excellent": "🏆", "Good": "👍", "Moderate": "⚠️", "Poor": "❌"}.get(rating, "❓")
        st.markdown(f'<div class="metric-card"><strong>Rating</strong><br>'
                   f'{rating_icon} <span class="{rating_color}">{rating}</span></div>',
                   unsafe_allow_html=True)

    with col3:
        coordinates = raw_data.get("coordinates", {})
        lat = coordinates.get("lat", 0)
        lng = coordinates.get("lng", 0)
        st.markdown(f'<div class="metric-card"><strong>Coordinates</strong><br>'
                   f'📍 {lat:.4f}, {lng:.4f}</div>',
                   unsafe_allow_html=True)

    with col4:
        analysis_date = raw_data.get("analysis_date", "Unknown")
        # Also check for created_at if analysis_date is not available
        if analysis_date == "Unknown":
            created_at = report_data.get("created_at")
            if created_at and hasattr(created_at, "strftime"):
                analysis_date = created_at.strftime("%Y-%m-%d %H:%M")
            elif isinstance(created_at, str):
                analysis_date = created_at

        st.markdown(f'<div class="metric-card"><strong>Analysis Date & Time</strong><br>'
                   f'📅 {analysis_date}</div>',
                   unsafe_allow_html=True)

    # Overall recommendation
    if recommendation:
        st.info(f"💡 **Overall Assessment**: {recommendation}")

    # Domain Scores Overview - Clean Display
    domain_analysis = raw_data.get("domain_analysis", {})
    if domain_analysis:
        st.markdown("**📊 Domain Scores**")

        # Use streamlit columns for clean rendering
        num_domains = len(domain_analysis)
        if num_domains > 0:
            # Create columns (max 4 per row)
            cols_per_row = min(num_domains, 4)
            cols = st.columns(cols_per_row)

            for i, (domain_name, domain_data) in enumerate(domain_analysis.items()):
                col_idx = i % cols_per_row

                with cols[col_idx]:
                    try:
                        if isinstance(domain_data, dict):
                            score = domain_data.get("score", 0)

                            if isinstance(score, (int, float)):
                                domain_display_name = domain_name.replace('_', ' ').title()

                                # Color based on score
                                if score >= 4.0:
                                    color = "🟢"
                                elif score >= 3.0:
                                    color = "🔵"
                                elif score >= 2.0:
                                    color = "🟡"
                                else:
                                    color = "🔴"

                                # Clean metric display
                                st.metric(
                                    label=f"{color} {domain_display_name}",
                                    value=f"{score:.1f}/5.0"
                                )
                            else:
                                st.metric(
                                    label=domain_name.replace('_', ' ').title(),
                                    value="N/A"
                                )

                    except Exception:
                        # Skip problematic domains silently
                        continue

                # Start new row after 4 columns
                if (i + 1) % 4 == 0 and i + 1 < num_domains:
                    cols = st.columns(min(num_domains - (i + 1), 4))

    st.divider()

    # Interactive Map showing location
    coordinates = raw_data.get("coordinates", {})
    lat = coordinates.get("lat", 0)
    lng = coordinates.get("lng", 0)

    if lat != 0 and lng != 0:
        st.subheader("📍 Location Map")

        # Create map data for teardrop markers
        map_data = pd.DataFrame({
            'lat': [lat],
            'lon': [lng],
            'tooltip': [f"{location_name}\n{lat:.4f}, {lng:.4f}"]
        })

        try:
            import pydeck as pdk

            # Use a high-quality glossy red pin
            map_data["icon_url"] = "https://cdn-icons-png.flaticon.com/512/2776/2776067.png"

            # Each row needs icon data
            map_data["icon"] = [{
                "url": url,
                "width": 128,    # bigger source image
                "height": 128,
                "anchorY": 128   # sit correctly on the point
            } for url in map_data["icon_url"]]

            # Define IconLayer
            icon_layer = pdk.Layer(
                "IconLayer",
                data=map_data,
                get_icon="icon",
                get_position=["lon", "lat"],
                get_size=6,
                size_scale=9,   # tweak size scale for visibility
                pickable=True,
            )

            # Viewport
            view_state = pdk.ViewState(
                latitude=map_data["lat"].mean(),
                longitude=map_data["lon"].mean(),
                zoom=10,
            )

            # Render with pydeck (lighter background)
            st.pydeck_chart(pdk.Deck(
                layers=[icon_layer],
                initial_view_state=view_state,
                map_style="light",
                tooltip={"text": "📍 {name}"}
            ))

        except Exception as e:
            st.warning(f"Pydeck failed ({e}), falling back to simple circles")
            st.map(map_data, zoom=10, size=100, color='#ff4444')




        # Show coordinates info
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Latitude", f"{lat:.6f}")
        with col2:
            st.metric("Longitude", f"{lng:.6f}")

    st.divider()

    # Executive Summary (moved before Domain Analysis)
    st.header("📋 Executive Summary")
    executive_summary = raw_data.get("executive_summary", {})

    if executive_summary:
        # Location Overview
        location_overview = executive_summary.get("location_overview", "")
        if location_overview:
            with st.expander("🌍 Location Overview", expanded=False):
                st.write(location_overview)

        col1, col2 = st.columns(2)

        with col1:
            # Key Strengths
            strengths = executive_summary.get("key_strengths", [])
            if strengths:
                with st.expander("💪 Key Strengths", expanded=False):
                    for i, strength in enumerate(strengths, 1):
                        st.write(f"**{i}.** ✅ {strength}")

            # Strategic Opportunities (if in executive summary)
            strategic_opportunities = executive_summary.get("strategic_opportunities", [])
            if strategic_opportunities:
                with st.expander("🚀 Strategic Opportunities", expanded=False):
                    for i, opportunity in enumerate(strategic_opportunities, 1):
                        st.write(f"**{i}.** 🎯 {opportunity}")

        with col2:
            # Key Challenges
            challenges = executive_summary.get("key_challenges", [])
            if challenges:
                with st.expander("⚠️ Key Challenges", expanded=False):
                    for i, challenge in enumerate(challenges, 1):
                        st.write(f"**{i}.** ⚡ {challenge}")

            # Critical Success Factors
            success_factors = executive_summary.get("critical_success_factors", [])
            if success_factors:
                with st.expander("🎯 Critical Success Factors", expanded=False):
                    for i, factor in enumerate(success_factors, 1):
                        st.write(f"**{i}.** 🔑 {factor}")

    st.divider()

    # Domain Analysis
    st.header("🔬 Domain Analysis")

    domain_analysis = raw_data.get("domain_analysis", {})
    structured_analysis = raw_data.get("structured_analysis", {})

    for domain_name, domain_data in domain_analysis.items():
        render_domain_analysis(domain_name, domain_data, structured_analysis)

    st.divider()

    # Phase 1 Deployment
    st.header("🚀 Phase 1 Deployment Plan")
    phase1 = raw_data.get("phase_1_deployment", {})

    if phase1:
        with st.expander("📋 Phase 1 Deployment Details", expanded=False):
            # Key Metrics Overview
            col1, col2, col3 = st.columns(3)

            with col1:
                capacity = phase1.get('recommended_capacity', 'N/A')
                st.markdown(f'<div class="metric-card"><strong>Recommended Capacity</strong><br>{capacity}</div>',
                           unsafe_allow_html=True)

            with col2:
                timeline = phase1.get('timeline', 'N/A')
                st.markdown(f'<div class="metric-card"><strong>Timeline</strong><br>{timeline}</div>',
                           unsafe_allow_html=True)

            with col3:
                investment = phase1.get('estimated_investment', 'N/A')
                st.markdown(f'<div class="metric-card"><strong>Estimated Investment</strong><br>{investment}</div>',
                           unsafe_allow_html=True)

            # Detailed planning sections
            col1, col2 = st.columns(2)

            with col1:
                # Priority Actions
                actions = phase1.get("priority_actions", [])
                if actions:
                    with st.expander("📋 Priority Actions", expanded=False):
                        for i, action in enumerate(actions, 1):
                            st.write(f"**{i}.** {action}")

                # Success Metrics (if available)
                success_metrics = phase1.get("success_metrics", [])
                if success_metrics:
                    with st.expander("📊 Success Metrics", expanded=False):
                        for i, metric in enumerate(success_metrics, 1):
                            st.write(f"**{i}.** 📈 {metric}")

            with col2:
                # Risk Mitigation
                mitigations = phase1.get("risk_mitigation", [])
                if mitigations:
                    with st.expander("🛡️ Risk Mitigation", expanded=False):
                        for i, mitigation in enumerate(mitigations, 1):
                            st.write(f"**{i}.** 🔒 {mitigation}")

                # Additional deployment details if available
                deployment_details = phase1.get("deployment_details", "")
                if deployment_details:
                    with st.expander("📋 Deployment Details", expanded=False):
                        st.write(deployment_details)

    # Strategic Analysis Section
    st.header("💼 Strategic Analysis")

    # Strategic Opportunities
    strategic_opps = raw_data.get("strategic_opportunities", [])
    if strategic_opps:
        with st.expander("🚀 Strategic Opportunities", expanded=False):
            for i, opportunity in enumerate(strategic_opps, 1):
                st.write(f"**{i}.** {opportunity}")

    # Strategic Recommendations
    strategic_rec = raw_data.get("strategic_recommendation", "")
    if strategic_rec:
        with st.expander("💡 Strategic Recommendation", expanded=False):
            st.write(strategic_rec)

    # Conclusion
    conclusion = raw_data.get("conclusion", "")
    if conclusion:
        with st.expander("🎯 Conclusion", expanded=False):
            st.write(conclusion)

    # Next Steps
    next_steps = raw_data.get("next_steps", [])
    if next_steps:
        with st.expander("📋 Next Steps", expanded=False):
            for i, step in enumerate(next_steps, 1):
                st.write(f"**{i}.** {step}")

    st.divider()

    # Data Gap Analysis
    data_gap_analysis = raw_data.get("data_gap_analysis", {})
    if data_gap_analysis:
        st.header("🔍 Data Gap Analysis")

        # Overall confidence
        overall_confidence = data_gap_analysis.get("overall_confidence", "")
        if overall_confidence:
            confidence_color = get_score_color(4.0 if overall_confidence == "high" else 3.0 if overall_confidence == "medium" else 2.0)
            st.markdown(f'<div class="metric-card"><strong>Overall Confidence:</strong> <span class="{confidence_color}">{overall_confidence.title()}</span></div>',
                       unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # Data Sources Used
            data_sources = data_gap_analysis.get("data_sources_used", [])
            if data_sources:
                with st.expander("📊 Data Sources Used", expanded=False):
                    for source in data_sources:
                        if isinstance(source, dict):
                            name = source.get("name", "Unknown")
                            source_type = source.get("type", "Unknown").replace("_", " ").title()
                            reliability = source.get("reliability", "Unknown").title()
                            last_updated = source.get("last_updated", "")

                            st.markdown(f"""
                            **{name}**
                            - Type: {source_type}
                            - Reliability: {reliability}
                            {f"- Last Updated: {last_updated}" if last_updated else ""}
                            """)

            # Data Gaps Identified
            data_gaps = data_gap_analysis.get("data_gaps_identified", [])
            if data_gaps:
                with st.expander("⚠️ Data Gaps Identified", expanded=False):
                    for gap in data_gaps:
                        st.write(f"• {gap}")

        with col2:
            # Third Party Requirements
            third_party = data_gap_analysis.get("third_party_requirements", [])
            if third_party:
                with st.expander("🤝 Third Party Requirements", expanded=False):
                    for requirement in third_party:
                        st.write(f"• {requirement}")

            # Assumptions Made
            assumptions = data_gap_analysis.get("assumptions_made", [])
            if assumptions:
                with st.expander("📝 Key Assumptions", expanded=False):
                    for assumption in assumptions:
                        if isinstance(assumption, dict):
                            assumption_text = assumption.get("assumption", "")
                            confidence = assumption.get("confidence_level", "")
                            category = assumption.get("category", "")
                            if assumption_text:
                                st.write(f"**{category}:** {assumption_text}" if category else f"• {assumption_text}")
                                if confidence:
                                    confidence_color = get_score_color(4.0 if confidence == "high" else 3.0 if confidence == "medium" else 2.0)
                                    st.markdown(f'<small>Confidence: <span class="{confidence_color}">{confidence.title()}</span></small>',
                                               unsafe_allow_html=True)
                        else:
                            st.write(f"• {assumption}")

        # Next Steps Priority
        priority_steps = data_gap_analysis.get("next_steps_priority", [])
        if priority_steps:
            with st.expander("🎯 Priority Actions to Address Gaps", expanded=False):
                for i, step in enumerate(priority_steps, 1):
                    st.write(f"**{i}.** {step}")

    if st.button("📄 Download Professional Report (PDF)", use_container_width=True, type="primary"):
        try:
            import weasyprint
            import io
            from datetime import datetime
            import re

            def clean_markdown(text):
                """Remove markdown formatting from text"""
                if not text:
                    return text or ""
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
                text = re.sub(r'\*(.*?)\*', r'\1', text)
                text = re.sub(r'_(.*?)_', r'\1', text)
                return text

            def extract_metrics_data(metrics, section_name):
                """Extract all metrics data into HTML tables, aligned with section"""
                if not metrics:
                    return ""

                html = '<div class="metrics-container">'

                if metrics.get("numerical_values"):
                    html += f"<h4>📊 {clean_markdown(section_name)} Numerical Metrics</h4>"
                    html += '<table class="metrics-table">'
                    html += "<tr><th>Metric</th><th>Value</th><th>Unit</th></tr>"
                    units = metrics.get("units", {})
                    for key, value in metrics["numerical_values"].items():
                        unit = units.get(key, "")
                        formatted_value = f"{value:.2f}" if isinstance(value, float) else str(value)
                        html += f"<tr><td>{clean_markdown(key.replace('_', ' ').title())}</td><td>{formatted_value}</td><td>{unit}</td></tr>"
                    html += "</table>"

                if metrics.get("percentages"):
                    html += f"<h4>📈 {clean_markdown(section_name)} Percentage Breakdown</h4>"
                    html += '<table class="metrics-table">'
                    html += "<tr><th>Metric</th><th>Percentage</th></tr>"
                    for key, value in metrics["percentages"].items():
                        formatted_value = f"{value:.1f}%" if isinstance(value, float) else f"{value}%"
                        html += f"<tr><td>{clean_markdown(key.replace('_', ' ').title())}</td><td>{formatted_value}</td></tr>"
                    html += "</table>"

                if metrics.get("ranges"):
                    html += f"<h4>📏 {clean_markdown(section_name)} Value Ranges</h4>"
                    html += '<table class="metrics-table">'
                    html += "<tr><th>Metric</th><th>Minimum</th><th>Maximum</th><th>Unit</th></tr>"
                    units = metrics.get("units", {})
                    for key, value in metrics["ranges"].items():
                        if isinstance(value, dict) and "min" in value and "max" in value:
                            unit = units.get(key, "")
                            min_val = f"{value['min']:.2f}" if isinstance(value['min'], float) else str(value['min'])
                            max_val = f"{value['max']:.2f}" if isinstance(value['max'], float) else str(value['max'])
                            html += f"<tr><td>{clean_markdown(key.replace('_', ' ').title())}</td><td>{min_val}</td><td>{max_val}</td><td>{unit}</td></tr>"
                    html += "</table>"

                html += "</div>"
                return html

            def extract_structured_analysis(structured_analysis, domain_name):
                """Extract structured analysis data for a domain, keeping tables aligned"""
                domain_data = structured_analysis.get(domain_name, {})
                if not domain_data or not isinstance(domain_data, dict):
                    return ""

                html = '<div class="structured-section">'
                skip_sections = ['phase_1', 'phase_1_deployment', 'deployment', 'recommendations']

                for section_key, section_data in domain_data.items():
                    if isinstance(section_data, dict) and not any(skip in section_key.lower() for skip in skip_sections):
                        section_name = section_data.get("name", section_key.replace("_", " ").title())
                        content = section_data.get("content", "")
                        sub_score = section_data.get("sub_score", -1)
                        key_points = section_data.get("key_points", [])
                        metrics = section_data.get("metrics", {})

                        if content or key_points or sub_score > 0 or metrics:
                            html += f'<div class="subsection" style="page-break-inside: avoid; break-inside: avoid-column;">'
                            html += f"<h4>{clean_markdown(section_name)}</h4>"
                            if sub_score > 0:
                                html += f"<p><strong>Score:</strong> {sub_score:.1f}/5.0</p>"
                            if content:
                                html += f"<p>{clean_markdown(content)}</p>"
                            if key_points:
                                html += "<ul>"
                                for point in key_points:
                                    html += f"<li>{clean_markdown(point)}</li>"
                                html += "</ul>"
                            if metrics:
                                html += extract_metrics_data(metrics, section_name)
                            html += "</div>"

                assumptions = domain_data.get("assumptions", [])
                if assumptions:
                    html += f'<div class="subsection" style="page-break-inside: avoid; break-inside: avoid-column;">'
                    html += "<h4>Assumptions</h4><ul>"
                    for assumption in assumptions:
                        html += f"<li>{clean_markdown(assumption)}</li>"
                    html += "</ul></div>"

                html += "</div>"
                return html

            # Initialize variables with defaults
            composite_score = raw_data.get("overall_suitability", {}).get("composite_score", 0.0)
            rating = raw_data.get("overall_suitability", {}).get("rating", "Unknown")
            recommendation = raw_data.get("overall_suitability", {}).get("recommendation", "")
            coordinates = raw_data.get("coordinates", {})
            lat = coordinates.get("lat", 0.0)
            lng = coordinates.get("lng", 0.0)
            analysis_date = raw_data.get("analysis_date", raw_data.get("created_at", "Unknown"))
            if isinstance(analysis_date, datetime):
                analysis_date = analysis_date.strftime("%Y-%m-%d %H:%M")
            domain_analysis = raw_data.get("domain_analysis", {})
            structured_analysis = raw_data.get("structured_analysis", {})

            # Generate HTML for PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Datacenter Analysis Report - {clean_markdown(location_name)}</title>
                <style>
                    @page {{ margin: 0.5in; size: A4; }}
                    body {{ font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4; color: #333; margin: 0 auto; max-width: 600px; }}
                    .cover-page {{ text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 10px; margin-bottom: 25px; page-break-after: always; }}
                    .cover-title {{ font-size: 22px; font-weight: bold; color: #1f77b4; margin-bottom: 8px; }}
                    .cover-subtitle {{ font-size: 14px; color: #666; margin-bottom: 20px; }}
                    .cover-metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 15px 0; }}
                    .cover-metric {{ background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px; text-align: center; }}
                    .cover-metric-label {{ font-size: 9px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
                    .cover-metric-value {{ font-size: 16px; font-weight: bold; color: #1f77b4; }}
                    h1 {{ font-size: 16px; margin: 12px 0 8px 0; color: #1f77b4; }}
                    h2 {{ font-size: 14px; margin: 10px 0 6px 0; color: #333; }}
                    h3 {{ font-size: 12px; margin: 8px 0 5px 0; color: #666; }}
                    h4 {{ font-size: 11px; margin: 6px 0 3px 0; color: #666; }}
                    .section {{ margin: 15px 0; page-break-inside: avoid; }}
                    .subsection {{ margin: 8px 0; break-inside: avoid-column; }}
                    .metrics-container {{ margin-top: 6px; break-inside: avoid-column; }}
                    .metrics-table {{ width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 9px; }}
                    .metrics-table th, .metrics-table td {{ border: 1px solid #dee2e6; padding: 4px 6px; text-align: left; }}
                    .metrics-table th {{ background: #f8f9fa; font-weight: bold; }}
                    .structured-section {{ page-break-inside: avoid; break-inside: avoid-column; }}
                    ul, ol {{ margin: 6px 0; padding-left: 15px; }}
                    li {{ margin: 2px 0; }}
                    p {{ margin: 4px 0; }}
                </style>
            </head>
            <body>
                <!-- Cover Page -->
                <div class="cover-page">
                    <div class="cover-title">{flag} {clean_markdown(location_name)}</div>
                    <div class="cover-subtitle">Datacenter Site Analysis Report</div>
                    <div class="cover-subtitle">{clean_markdown(country)}</div>
                    <div class="cover-metrics">
                        <div class="cover-metric">
                            <div class="cover-metric-label">Overall Score</div>
                            <div class="cover-metric-value">{composite_score:.1f}/5.0</div>
                        </div>
                        <div class="cover-metric">
                            <div class="cover-metric-label">Rating</div>
                            <div class="cover-metric-value">{clean_markdown(rating)}</div>
                        </div>
                        <div class="cover-metric">
                            <div class="cover-metric-label">Coordinates</div>
                            <div class="cover-metric-value">{lat:.4f}, {lng:.4f}</div>
                        </div>
                        <div class="cover-metric">
                            <div class="cover-metric-label">Analysis Date</div>
                            <div class="cover-metric-value" style="font-size: 12px;">{clean_markdown(analysis_date)}</div>
                        </div>
                    </div>
                    <!-- Domain Scores -->
                    <div style="margin-top: 20px;">
                        <div style="font-size: 12px; font-weight: bold; margin-bottom: 10px; color: #1f77b4;">📊 Domain Performance</div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px;">
            """

            for domain_name, domain_data_item in domain_analysis.items():
                score = domain_data_item.get("score", 0) if isinstance(domain_data_item, dict) else 0
                if isinstance(score, (int, float)):
                    domain_display_name = clean_markdown(domain_name.replace('_', ' ').title())
                    score_color = '#28a745' if score >= 4 else '#17a2b8' if score >= 3 else '#ffc107' if score >= 2 else '#dc3545'
                    html_content += f"""
                        <div style="background: white; border: 1px solid #dee2e6; border-radius: 4px; padding: 6px; text-align: center; font-size: 9px;">
                            <div style="color: #666; margin-bottom: 2px;">{domain_display_name}</div>
                            <div style="font-weight: bold; color: {score_color};">{score:.1f}/5.0</div>
                        </div>
                    """

            html_content += f"""
                        </div>
                    </div>
                    <div style="background: white; border-radius: 5px; padding: 12px; margin-top: 15px; text-align: left; font-size: 10px;">
                        <strong>Assessment:</strong> {clean_markdown(recommendation)}
                    </div>
                </div>
            """

            # Executive Summary
            executive_summary = raw_data.get("executive_summary", {})
            if executive_summary:
                html_content += '<div class="section"><h2>📋 Executive Summary</h2>'
                if executive_summary.get("location_overview"):
                    html_content += f'<div class="subsection"><h3>Location Overview</h3><p>{clean_markdown(executive_summary["location_overview"])}</p></div>'
                if executive_summary.get("key_strengths"):
                    html_content += '<div class="subsection"><h3>Key Strengths</h3><ul>'
                    for strength in executive_summary["key_strengths"]:
                        html_content += f"<li>{clean_markdown(strength)}</li>"
                    html_content += "</ul></div>"
                if executive_summary.get("key_challenges"):
                    html_content += '<div class="subsection"><h3>Key Challenges</h3><ul>'
                    for challenge in executive_summary["key_challenges"]:
                        html_content += f"<li>{clean_markdown(challenge)}</li>"
                    html_content += "</ul></div>"
                if executive_summary.get("strategic_opportunities"):
                    html_content += '<div class="subsection"><h3>Strategic Opportunities</h3><ul>'
                    for opportunity in executive_summary["strategic_opportunities"]:
                        html_content += f"<li>{clean_markdown(opportunity)}</li>"
                    html_content += "</ul></div>"
                if executive_summary.get("critical_success_factors"):
                    html_content += '<div class="subsection"><h3>Critical Success Factors</h3><ul>'
                    for factor in executive_summary["critical_success_factors"]:
                        html_content += f"<li>{clean_markdown(factor)}</li>"
                    html_content += "</ul></div>"
                html_content += "</div>"

            # Domain Analysis
            if domain_analysis:
                html_content += '<div class="section"><h2>🔬 Detailed Domain Analysis</h2>'
                for domain_name, domain_data_item in domain_analysis.items():
                    if isinstance(domain_data_item, dict):
                        domain_display_name = clean_markdown(domain_name.replace('_', ' ').title())
                        score = domain_data_item.get("score", 0)
                        summary = domain_data_item.get("summary", "")
                        key_findings = domain_data_item.get("key_findings", [])

                        html_content += f'<div class="subsection domain-section" style="page-break-inside: avoid; break-inside: avoid-column;"><h3>{domain_display_name} (Score: {score:.1f}/5.0)</h3>'
                        if summary:
                            html_content += f'<p><strong>Summary:</strong> {clean_markdown(summary)}</p>'
                        if key_findings:
                            html_content += '<h4>Key Findings</h4><ul>'
                            for finding in key_findings:
                                html_content += f'<li>{clean_markdown(finding)}</li>'
                            html_content += '</ul>'
                        structured_domain_html = extract_structured_analysis(structured_analysis, domain_name)
                        if structured_domain_html:
                            html_content += structured_domain_html
                        html_content += "</div>"
                html_content += "</div>"

            # Phase 1 Deployment
            phase1 = raw_data.get("phase_1_deployment", {})
            if phase1:
                html_content += '<div class="section"><h2>🚀 Phase 1 Deployment</h2>'
                key_fields = ['recommended_capacity', 'timeline', 'estimated_investment']
                for field in key_fields:
                    if phase1.get(field):
                        html_content += f'<div class="subsection"><p><strong>{clean_markdown(field.replace("_", " ").title())}:</strong> {clean_markdown(str(phase1[field]))}</p></div>'
                if phase1.get("priority_actions"):
                    html_content += '<div class="subsection"><h3>Priority Actions</h3><ul>'
                    for action in phase1["priority_actions"]:
                        html_content += f'<li>{clean_markdown(action)}</li>'
                    html_content += '</ul></div>'
                if phase1.get("success_metrics"):
                    html_content += '<div class="subsection"><h3>Success Metrics</h3><ul>'
                    for metric in phase1["success_metrics"]:
                        html_content += f'<li>{clean_markdown(metric)}</li>'
                    html_content += '</ul></div>'
                if phase1.get("risk_mitigation"):
                    html_content += '<div class="subsection"><h3>Risk Mitigation</h3><ul>'
                    for mitigation in phase1["risk_mitigation"]:
                        html_content += f'<li>{clean_markdown(mitigation)}</li>'
                    html_content += '</ul></div>'
                if phase1.get("deployment_details"):
                    html_content += f'<div class="subsection"><h3>Deployment Details</h3><p>{clean_markdown(phase1["deployment_details"])}</p></div>'
                html_content += '</div>'

            # Strategic Analysis
            html_content += '<div class="section"><h2>💼 Strategic Analysis</h2>'
            strategic_opps = raw_data.get("strategic_opportunities", [])
            if strategic_opps:
                html_content += '<div class="subsection"><h3>Strategic Opportunities</h3><ul>'
                for opportunity in strategic_opps:
                    html_content += f'<li>{clean_markdown(opportunity)}</li>'
                html_content += '</ul></div>'
            strategic_rec = raw_data.get("strategic_recommendation", "")
            if strategic_rec:
                html_content += f'<div class="subsection"><h3>Strategic Recommendation</h3><p>{clean_markdown(strategic_rec)}</p></div>'
            conclusion = raw_data.get("conclusion", "")
            if conclusion:
                html_content += f'<div class="subsection"><h3>Conclusion</h3><p>{clean_markdown(conclusion)}</p></div>'
            next_steps = raw_data.get("next_steps", [])
            if next_steps:
                html_content += '<div class="subsection"><h3>Next Steps</h3><ul>'
                for step in next_steps:
                    html_content += f'<li>{clean_markdown(step)}</li>'
                html_content += '</ul></div>'
            html_content += '</div>'

            # Data Gap Analysis
            data_gap_analysis = raw_data.get("data_gap_analysis", {})
            if data_gap_analysis:
                html_content += '<div class="section"><h2>🔍 Data Gap Analysis</h2>'
                if data_gap_analysis.get("overall_confidence"):
                    html_content += f'<div class="subsection"><p><strong>Overall Confidence:</strong> {clean_markdown(data_gap_analysis["overall_confidence"].title())}</p></div>'
                if data_gap_analysis.get("data_sources_used"):
                    html_content += '<div class="subsection"><h3>Data Sources Used</h3><ul>'
                    for source in data_gap_analysis["data_sources_used"]:
                        if isinstance(source, dict):
                            name = source.get("name", "Unknown")
                            source_type = source.get("type", "Unknown").replace("_", " ").title()
                            reliability = source.get("reliability", "Unknown").title()
                            last_updated = source.get("last_updated", "")
                            html_content += f'<li>{clean_markdown(name)} ({source_type}, Reliability: {reliability}{f", Last Updated: {last_updated}" if last_updated else ""})</li>'
                        else:
                            html_content += f'<li>{clean_markdown(source)}</li>'
                    html_content += '</ul></div>'
                if data_gap_analysis.get("data_gaps_identified"):
                    html_content += '<div class="subsection"><h3>Data Gaps Identified</h3><ul>'
                    for gap in data_gap_analysis["data_gaps_identified"]:
                        html_content += f'<li>{clean_markdown(gap)}</li>'
                    html_content += '</ul></div>'
                if data_gap_analysis.get("third_party_requirements"):
                    html_content += '<div class="subsection"><h3>Third Party Requirements</h3><ul>'
                    for requirement in data_gap_analysis["third_party_requirements"]:
                        html_content += f'<li>{clean_markdown(requirement)}</li>'
                    html_content += '</ul></div>'
                if data_gap_analysis.get("assumptions_made"):
                    html_content += '<div class="subsection"><h3>Key Assumptions</h3><ul>'
                    for assumption in data_gap_analysis["assumptions_made"]:
                        if isinstance(assumption, dict):
                            assumption_text = assumption.get("assumption", "")
                            confidence = assumption.get("confidence_level", "")
                            category = assumption.get("category", "")
                            html_content += f'<li>{clean_markdown(category + ": " + assumption_text) if category else clean_markdown(assumption_text)}'
                            if confidence:
                                html_content += f' (Confidence: {confidence.title()})</li>'
                        else:
                            html_content += f'<li>{clean_markdown(assumption)}</li>'
                    html_content += '</ul></div>'
                if data_gap_analysis.get("next_steps_priority"):
                    html_content += '<div class="subsection"><h3>Priority Actions to Address Gaps</h3><ul>'
                    for step in data_gap_analysis["next_steps_priority"]:
                        html_content += f'<li>{clean_markdown(step)}</li>'
                    html_content += '</ul></div>'
                html_content += '</div>'

            # Close HTML
            html_content += f"""
                <p style="text-align: center; margin-top: 30px; font-size: 10px; color: #666;">
                    Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Datacenter Analysis Report
                </p>
            </body>
            </html>
            """

            # Generate PDF
            pdf_buffer = io.BytesIO()
            weasyprint.HTML(string=html_content).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)

            # Download button
            st.download_button(
                label="💾 Download PDF Report",
                data=pdf_buffer.getvalue(),
                file_name=f"datacenter_report_{raw_data.get('location', 'unknown').replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
            st.success("📄 PDF generated successfully!")

        except ImportError:
            st.error("📄 PDF generation requires weasyprint. Install with: uv add weasyprint or pip install weasyprint")
            text_content = f"""
    DATACENTER ANALYSIS REPORT
    {flag} {location_name}
    Analysis for {country}

    OVERALL METRICS:
    - Score: {composite_score:.1f}/5.0
    - Rating: {rating}
    - Coordinates: {lat:.4f}, {lng:.4f}
    - Analysis Date: {analysis_date}

    {f'OVERALL ASSESSMENT: {recommendation}' if recommendation else ''}

    DOMAIN SCORES:
    """
            for domain_name, domain_data_item in domain_analysis.items():
                score = domain_data_item.get("score", 0) if isinstance(domain_data_item, dict) else 0
                if isinstance(score, (int, float)):
                    text_content += f"- {clean_markdown(domain_name.replace('_', ' ').title())}: {score:.1f}/5.0\n"
            st.download_button(
                label="📄 Download Report (Text)",
                data=text_content,
                file_name=f"datacenter_report_{raw_data.get('location', 'unknown').replace(' ', '_')}.txt",
                mime="text/plain"
            )
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            st.info("💡 Please ensure weasyprint is installed: uv add weasyprint")