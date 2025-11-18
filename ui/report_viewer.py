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

def _get_verification_badge(verification_level: str) -> str:
    """Get HTML badge for verification level"""
    badge_styles = {
        "verified_by_public_source": '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;">✓ Verified by Public Source</span>',
        "verified_by_transactional": '<span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;">✓✓ Investment-Grade</span>',
        "model_inference": '<span style="background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;">⚠ Model Inference - Needs Validation</span>',
        "unknown_requires_utility_letter": '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;">⚠ Unknown - Requires Utility Letter</span>',
        "assumption_based_on_region": '<span style="background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;">~ Regional Assumption</span>'
    }
    return badge_styles.get(verification_level, f'<span style="background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;">{verification_level}</span>')

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

def render_metrics_table(metrics: Dict[str, Any], section_name: str) -> None:
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
                    st.dataframe(df, width='stretch', hide_index=True)
        else:
            # Single table, no tabs needed
            _, df = tab_data[0]
            st.dataframe(df, width='stretch', hide_index=True)

def render_domain_analysis(domain_name: str, domain_data: Dict[str, Any], structured_analysis: Dict[str, Any]) -> None:
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
            # Check if all subsections are empty/null
            subsection_keys = [k for k in domain_structured.keys() if k not in ['assumptions', 'overall_score', 'phase_1_deployment', 'phase_1_recommendations', 'sources', 'key_insights', 'executive_summary', 'data_gaps', 'third_party_verification', 'no_go_gates', 'caution_flags', 'provenance_badges', 'distance_measurements']]
            # Check if subsections have actual RichSection structure (name, content, metrics, etc.)
            populated_subsections = [k for k in subsection_keys if isinstance(domain_structured.get(k), dict) and len(domain_structured.get(k, {})) > 0]

            if len(subsection_keys) > 0 and len(populated_subsections) == 0:
                st.warning(f"⚠️ **Detailed subsections incomplete for this domain** - Showing summary and sources. This may indicate incomplete data collection.")
            elif len(populated_subsections) > 0:
                st.write("**📊 Detailed Analysis Sections:**")

            # Iterate through all subsections in this domain
            for section_key, section_data in domain_structured.items():
                if isinstance(section_data, dict):
                    # Skip non-section data like assumptions and overall metrics
                    if section_key in ['assumptions', 'overall_score', 'phase_1_deployment', 'phase_1_recommendations']:
                        continue

                    section_name = section_data.get("name") or section_key.replace("_", " ").title()
                    content = section_data.get("content", "")
                    sub_score = section_data.get("sub_score", -1)
                    metrics = section_data.get("metrics", {})
                    key_points = section_data.get("key_points", [])
                    verification_metadata = section_data.get("verification_metadata", {})

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

                        # Verification badges (for power capacity section)
                        if verification_metadata:
                            st.write("**🔍 Verification Status:**")
                            for claim, verification_level in verification_metadata.items():
                                badge = _get_verification_badge(verification_level)
                                claim_display = claim.replace("_", " ").title()
                                st.markdown(f"• **{claim_display}**: {badge}", unsafe_allow_html=True)

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

        # Show sources if available
        if domain_structured and 'sources' in domain_structured:
            sources = domain_structured['sources']
            st.divider()
            if sources and isinstance(sources, list) and len(sources) > 0:
                st.write(f"**📚 Sources & References ({len(sources)} sources)**")
                with st.expander("View all sources", expanded=False):
                    for idx, source in enumerate(sources, 1):
                        if isinstance(source, dict):
                            url = source.get("url", "")
                            title = source.get("title", "Unknown Source")
                            date = source.get("date", "")
                            snippet = source.get("snippet", "")
                            distance_km = source.get("distance_from_site_km")
                            spatial_precision = source.get("spatial_precision", "")

                            st.markdown(f"""
                            **{idx}. {title}**
                            {f"📅 {date}  " if date else ""}
                            {f"📍 **{distance_km} km from site**  " if distance_km is not None else ""}
                            {f"🎯 {spatial_precision}  " if spatial_precision else ""}
                            {f"🔗 [{url}]({url})  " if url else ""}
                            {f"*{snippet}*" if snippet else ""}
                            """)
                            if idx < len(sources):
                                st.divider()
                        elif isinstance(source, str):
                            st.write(f"{idx}. {source}")
            else:
                st.info("📚 **Sources & References:** No sources available - data collection pending")

def render_report_viewer(report_id: int) -> None:
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

    st.divider()

    # Investment-Grade Scoring Breakdown
    st.markdown("### 📊 Investment-Grade Scoring Breakdown")

    weighted_scores = raw_data.get("weighted_domain_scores", [])
    all_caution_flags = raw_data.get("all_caution_flags", [])

    if weighted_scores:
        # Check for NO-GO gates and explain scoring logic
        has_no_go = any(ws.get("no_go_gates_triggered", 0) > 0 for ws in weighted_scores)
        total_caution_penalty = sum(f.get("severity_points", 0) for f in all_caution_flags)

        if has_no_go:
            st.error("🚫 **CRITICAL: NO-GO GATE TRIGGERED**")
            st.markdown("""
            **Scoring Override:** One or more critical failure conditions have been detected. When a NO-GO gate is triggered:
            - All domain contributions are set to **0.0** (regardless of individual scores)
            - Final composite score becomes **0.0/5.0**
            - Site is marked as **NOT VIABLE** for datacenter development

            **Critical failures must be resolved before proceeding with investment.**
            """)
        elif total_caution_penalty > 0:
            # Calculate regional vs independent breakdown
            regional_baseline_keywords = [
                # Climate/Weather (regional norms)
                'flood', 'coastal', 'temperature', 'humidity', 'wind', 'hurricane', 'storm',
                'precipitation', 'climate', 'heat', 'cold', 'thermal', 'freezing', 'snow', 'ice',
                'sea level', 'slr', 'storm surge', 'typhoon', 'cyclone',
                # Infrastructure (regional baseline)
                'pile', 'foundation', 'soil', 'bearing', 'geotechnical', 'groundwater',
                'drainage', 'freeboard', 'elevation', 'topography', 'grade', 'grading', 'fill',
                'water', 'wastewater', 'water consumption', 'wue', 'cooling',
                'transportation', 'highway', 'rail', 'road access', 'logistics',
                # Energy/Efficiency (regional baseline)
                'pue', 'power', 'grid', 'utility', 'electrical',
                # Regulatory (regional norms)
                'permitting', 'permit', 'zoning', 'public hearing', 'cup', 'regulatory',
                'compliance', 'municipal', 'county', 'local regulation'
            ]

            independent_hazard_keywords = [
                # Site-specific hazards
                'seismic', 'earthquake', 'liquefaction', 'wildfire', 'fire',
                'tsunami', 'volcano', 'subsidence', 'karst', 'sinkhole',
                'landslide', 'avalanche', 'tornado',
                # Resource scarcity
                'water stress', 'water scarcity', 'drought', 'aqueduct',
                # Site-specific environmental
                'contamination', 'endangered species', 'brownfield', 'hazmat', 'wetland',
                'protected area', 'conservation',
                # Business/market
                'ixp', 'bandwidth', 'peering', 'demand', 'lease', 'market',
                'data sovereignty', 'cloud act', 'lawful access',
                # Design choices
                'pue optimization', 'design choice'
            ]

            def is_regional_baseline_ui(flag):
                category_lower = flag.get('category', '').lower()
                if any(keyword in category_lower for keyword in independent_hazard_keywords):
                    return False
                return any(keyword in category_lower for keyword in regional_baseline_keywords)

            regional_flags = [f for f in all_caution_flags if is_regional_baseline_ui(f)]
            independent_flags = [f for f in all_caution_flags if f not in regional_flags]

            regional_penalty = max([f.get('severity_points', 0.0) for f in regional_flags], default=0.0)
            independent_penalty = sum([f.get('severity_points', 0.0) for f in independent_flags])

            st.warning(f"⚠️ **Scoring Note:** {len(all_caution_flags)} caution flags identified (-{total_caution_penalty:.2f} point total penalty)")

            if regional_flags:
                st.info(f"""
                📊 **Penalty Breakdown:**
                - **Regional Baseline Adjustments:** {len(regional_flags)} flags → **-{regional_penalty:.2f}** points (max penalty, not stacked)
                - **Independent Hazards:** {len(independent_flags)} flags → **-{independent_penalty:.2f}** points (summed)

                💡 **Why regional flags don't stack:** Regional baseline flags (coastal, climate, foundations) reflect local construction norms and share geography-based risks. We apply the MAX penalty to avoid excessive stacking. Independent hazards (seismic, wildfire) are summed as they represent distinct risks.
                """)

            st.markdown("""
            **How scoring works:**
            1. Each domain contributes: `Raw Score × Weight` to the total
            2. Regional baseline flags: **MAX penalty applied** (not summed to avoid stacking)
            3. Independent hazard flags: **Penalties summed** (distinct risks)
            4. Final score = `Weighted Sum - Total Penalties` (minimum 1.0)
            """)
        else:
            st.success("✅ **Clean Analysis:** No NO-GO gates triggered, no caution flags")

        st.markdown("---")

        with st.expander("💎 Weighted Domain Contributions", expanded=True):
            # Create scoring breakdown table
            scoring_data = []
            total_weighted = 0

            for ws in weighted_scores:
                domain_name = ws.get("domain_name", "Unknown").replace("_", " ").title()
                raw_score = ws.get("raw_score", 0)
                weight = ws.get("weight", 0)
                contribution = ws.get("weighted_contribution", 0)
                no_go_count = ws.get("no_go_gates_triggered", 0)
                caution_count = ws.get("caution_flags_count", 0)

                total_weighted += contribution

                scoring_data.append({
                    "Domain": domain_name,
                    "Raw Score": f"{raw_score:.2f}/5.0",
                    "Weight": f"{weight * 100:.0f}%",
                    "Contribution": f"{contribution:.3f}",
                    "⛔ NO-GO": no_go_count,
                    "⚠️ Caution": caution_count
                })

            df = pd.DataFrame(scoring_data)
            st.dataframe(df, width='stretch', hide_index=True)

            # Calculate penalty using regional baseline logic (matching synthesis_agents.py)
            regional_baseline_keywords_calc = [
                'flood', 'coastal', 'temperature', 'humidity', 'wind', 'hurricane', 'storm',
                'precipitation', 'climate', 'heat', 'cold', 'thermal', 'sea level', 'slr',
                'pile', 'foundation', 'soil', 'bearing', 'geotechnical', 'groundwater',
                'drainage', 'water', 'wastewater', 'transportation', 'permitting', 'permit',
                'zoning', 'regulatory', 'pue', 'power', 'grid', 'utility', 'cooling'
            ]

            independent_hazard_keywords_calc = [
                'seismic', 'earthquake', 'liquefaction', 'wildfire', 'fire',
                'water stress', 'water scarcity', 'drought', 'aqueduct',
                'contamination', 'endangered species', 'brownfield', 'hazmat', 'wetland',
                'ixp', 'bandwidth', 'peering', 'demand', 'lease', 'market',
                'data sovereignty', 'cloud act'
            ]

            def is_regional_calc(flag):
                cat_lower = flag.get('category', '').lower()
                if any(kw in cat_lower for kw in independent_hazard_keywords_calc):
                    return False
                return any(kw in cat_lower for kw in regional_baseline_keywords_calc)

            regional_flags_calc = [f for f in all_caution_flags if is_regional_calc(f)]
            independent_flags_calc = [f for f in all_caution_flags if f not in regional_flags_calc]

            regional_penalty = max([f.get('severity_points', 0.0) for f in regional_flags_calc], default=0.0)
            independent_penalty = sum([f.get('severity_points', 0.0) for f in independent_flags_calc])
            total_penalty = regional_penalty + independent_penalty

            # Apply 50% cap
            capped_penalty = min(total_penalty, total_weighted * 0.5)

            # Show calculation
            st.markdown("**Composite Score Calculation:**")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Weighted Subtotal", f"{total_weighted:.2f}/5.0")
            with col2:
                penalty_color = "🔴" if capped_penalty > 1.0 else "🟡" if capped_penalty > 0.3 else "🟢"
                st.metric("Caution Penalties", f"{penalty_color} -{capped_penalty:.2f}")
                if capped_penalty < total_penalty:
                    st.caption(f"(Capped from -{total_penalty:.2f})")
            with col3:
                # Use actual composite score from data instead of recalculating
                # (synthesis agent applies additional logic like NO-GO overrides)
                st.metric("Final Composite", f"{composite_score:.2f}/5.0",
                         delta=f"{composite_score - total_weighted:.2f}")

    st.divider()

    # Domain Scores Overview - Clean Display
    domain_analysis = raw_data.get("domain_analysis", {})
    if domain_analysis:
        st.markdown("**📊 Domain Scores**")

        # Use streamlit columns for clean rendering
        domains_list = list(domain_analysis.items())
        num_domains = len(domains_list)

        if num_domains > 0:
            # Process domains in rows of 4
            for row_start in range(0, num_domains, 4):
                row_domains = domains_list[row_start:row_start + 4]
                cols = st.columns(4)

                for col_idx, (domain_name, domain_data) in enumerate(row_domains):
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
                            continue

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

    # NO-GO Gates Dashboard
    st.header("🚫 NO-GO Gate Analysis")

    all_no_go_gates = raw_data.get("all_no_go_gates", [])

    if all_no_go_gates:
        triggered_gates = [g for g in all_no_go_gates if g.get("triggered", False)]
        passed_gates = [g for g in all_no_go_gates if not g.get("triggered", False)]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("✅ Passed Gates", len(passed_gates))
        with col2:
            alert_color = "🔴" if len(triggered_gates) > 0 else "🟢"
            st.metric(f"{alert_color} Triggered Gates", len(triggered_gates))

        # Show triggered gates first (critical)
        if triggered_gates:
            with st.expander(f"⛔ TRIGGERED NO-GO GATES ({len(triggered_gates)})", expanded=True):
                for idx, gate in enumerate(triggered_gates, 1):
                    st.markdown(f"### {idx}. 🚨 {gate.get('gate_type', 'Unknown Gate')}")

                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Reason:** {gate.get('reason', 'N/A')}")
                        if gate.get('standard_reference'):
                            st.markdown(f"**Standard:** {gate.get('standard_reference')}")

                    with col2:
                        mitigation_possible = gate.get('mitigation_possible', False)
                        if mitigation_possible:
                            st.success("✅ Mitigation Possible")
                            if gate.get('mitigation_cost'):
                                st.markdown(f"**Cost:** {gate.get('mitigation_cost')}")
                        else:
                            st.error("❌ Cannot Mitigate")

                    if idx < len(triggered_gates):
                        st.divider()

        # Show passed gates (collapsed by default)
        if passed_gates:
            with st.expander(f"✅ PASSED NO-GO GATES ({len(passed_gates)})", expanded=False):
                cols_per_row = 3
                for i in range(0, len(passed_gates), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for col_idx in range(cols_per_row):
                        if i + col_idx < len(passed_gates):
                            gate = passed_gates[i + col_idx]
                            with cols[col_idx]:
                                st.markdown(f"✅ **{gate.get('gate_type', 'Unknown')}**")

    st.divider()

    # Caution Flags with Penalties
    st.header("⚠️ Caution Flags & Risk Mitigation")

    if all_caution_flags:
        # Classify flags as regional baseline vs independent
        regional_baseline_keywords = [
            # Climate/Weather (regional norms)
            'flood', 'coastal', 'temperature', 'humidity', 'wind', 'hurricane', 'storm',
            'precipitation', 'climate', 'heat', 'cold', 'thermal', 'freezing', 'snow', 'ice',
            'sea level', 'slr', 'storm surge', 'typhoon', 'cyclone',
            # Infrastructure (regional baseline)
            'pile', 'foundation', 'soil', 'bearing', 'geotechnical', 'groundwater',
            'drainage', 'freeboard', 'elevation', 'topography', 'grade', 'grading', 'fill',
            'water', 'wastewater', 'water consumption', 'wue', 'cooling',
            'transportation', 'highway', 'rail', 'road access', 'logistics',
            # Energy/Efficiency (regional baseline)
            'pue', 'power', 'grid', 'utility', 'electrical',
            # Regulatory (regional norms)
            'permitting', 'permit', 'zoning', 'public hearing', 'cup', 'regulatory',
            'compliance', 'municipal', 'county', 'local regulation'
        ]

        independent_hazard_keywords = [
            # Site-specific hazards
            'seismic', 'earthquake', 'liquefaction', 'wildfire', 'fire',
            'tsunami', 'volcano', 'subsidence', 'karst', 'sinkhole',
            'landslide', 'avalanche', 'tornado',
            # Resource scarcity
            'water stress', 'water scarcity', 'drought', 'aqueduct',
            # Site-specific environmental
            'contamination', 'endangered species', 'brownfield', 'hazmat', 'wetland',
            'protected area', 'conservation',
            # Business/market
            'ixp', 'bandwidth', 'peering', 'demand', 'lease', 'market',
            'data sovereignty', 'cloud act', 'lawful access',
            # Design choices
            'pue optimization', 'design choice'
        ]

        def is_regional_baseline(flag):
            category_lower = flag.get('category', '').lower()
            if any(keyword in category_lower for keyword in independent_hazard_keywords):
                return False
            return any(keyword in category_lower for keyword in regional_baseline_keywords)

        # Group by severity
        high_severity = [f for f in all_caution_flags if f.get("severity", "").lower() == "high"]
        medium_severity = [f for f in all_caution_flags if f.get("severity", "").lower() == "medium"]
        low_severity = [f for f in all_caution_flags if f.get("severity", "").lower() == "low"]

        # Calculate penalty breakdown
        regional_flags = [f for f in all_caution_flags if is_regional_baseline(f)]
        independent_flags = [f for f in all_caution_flags if f not in regional_flags]
        regional_penalty = max([f.get('severity_points', 0.0) for f in regional_flags], default=0.0)
        independent_penalty = sum([f.get('severity_points', 0.0) for f in independent_flags])
        total_penalty_uncapped = regional_penalty + independent_penalty

        st.info(f"📊 **Total Flags:** {len(all_caution_flags)} ({len(regional_flags)} regional baseline, {len(independent_flags)} independent)")
        st.caption(f"**Penalty Breakdown:** Regional max: -{regional_penalty:.2f} | Independent sum: -{independent_penalty:.2f} | Total: -{total_penalty_uncapped:.2f} (applied with 50% cap)")
        if regional_flags:
            st.caption("🌍 Regional baseline flags (max penalty applied): Coastal, climate, and foundation flags reflect local construction norms")

        # High Severity Flags
        if high_severity:
            high_penalty = sum(f.get("severity_points", 0) for f in high_severity)
            with st.expander(f"🔴 HIGH SEVERITY ({len(high_severity)} flags, -{high_penalty:.2f} penalty)", expanded=True):
                for idx, flag in enumerate(high_severity, 1):
                    # Show regional baseline indicator
                    is_regional = is_regional_baseline(flag)
                    regional_badge = "🌍 **Regional Baseline**" if is_regional else "⚠️ **Independent Hazard**"

                    st.markdown(f"### {idx}. {flag.get('category', 'Unknown Category')} {regional_badge}")

                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Issue:** {flag.get('description', 'N/A')}")
                        st.markdown(f"**Mitigation:** {flag.get('mitigation_plan', 'TBD')}")

                    with col2:
                        penalty_label = "Max Penalty" if is_regional else "Penalty"
                        st.error(f"**{penalty_label}:** -{flag.get('severity_points', 0):.2f} points")
                        if flag.get('cost_impact'):
                            st.markdown(f"**Cost:** {flag.get('cost_impact')}")
                        if flag.get('timeline_impact'):
                            st.markdown(f"**Timeline:** {flag.get('timeline_impact')}")

                    if idx < len(high_severity):
                        st.divider()

        # Medium Severity Flags
        if medium_severity:
            medium_penalty = sum(f.get("severity_points", 0) for f in medium_severity)
            with st.expander(f"🟡 MEDIUM SEVERITY ({len(medium_severity)} flags, -{medium_penalty:.2f} penalty)", expanded=False):
                for idx, flag in enumerate(medium_severity, 1):
                    is_regional = is_regional_baseline(flag)
                    regional_icon = "🌍" if is_regional else "⚠️"
                    st.markdown(f"{regional_icon} **{idx}. {flag.get('category', 'Unknown')}** (Penalty: -{flag.get('severity_points', 0):.2f})")
                    st.markdown(f"• {flag.get('description', 'N/A')}")
                    st.markdown(f"• Mitigation: {flag.get('mitigation_plan', 'TBD')}")
                    if flag.get('cost_impact'):
                        st.caption(f"💰 {flag.get('cost_impact')}")
                    if idx < len(medium_severity):
                        st.markdown("---")

        # Low Severity Flags
        if low_severity:
            low_penalty = sum(f.get("severity_points", 0) for f in low_severity)
            with st.expander(f"🟢 LOW SEVERITY ({len(low_severity)} flags, -{low_penalty:.2f} penalty)", expanded=False):
                for idx, flag in enumerate(low_severity, 1):
                    is_regional = is_regional_baseline(flag)
                    regional_icon = "🌍" if is_regional else "⚠️"
                    st.markdown(f"{regional_icon} **{idx}. {flag.get('category', 'Unknown')}** (Penalty: -{flag.get('severity_points', 0):.2f})")
                    st.caption(f"{flag.get('description', 'N/A')}")

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

    if st.button("📄 Download Professional Report (PDF)", width='stretch', type="primary"):
        try:
            from xhtml2pdf import pisa
            import io
            from datetime import datetime
            import re
            import sys
            from contextlib import redirect_stdout

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
                skip_sections = ['phase_1', 'phase_1_deployment', 'deployment', 'recommendations', 'assumptions', 'overall_score', 'sources', 'key_insights', 'executive_summary', 'data_gaps', 'third_party_verification', 'no_go_gates', 'caution_flags', 'provenance_badges', 'distance_measurements']

                # Count how many actual subsections exist
                subsection_count = 0
                for section_key, section_data in domain_data.items():
                    if isinstance(section_data, dict) and not any(skip in section_key.lower() for skip in skip_sections):
                        content = section_data.get("content", "")
                        key_points = section_data.get("key_points", [])
                        sub_score = section_data.get("sub_score", -1)
                        metrics = section_data.get("metrics", {})
                        if content or key_points or sub_score > 0 or metrics:
                            subsection_count += 1

                # Show warning if no subsections populated
                if subsection_count == 0:
                    html += '<div class="subsection" style="background-color: #fff3cd; padding: 10px; border-left: 3px solid #ffc107; margin: 10px 0;">'
                    html += "<p><strong>⚠️ Detailed subsections incomplete for this domain</strong> - Showing summary and sources. This may indicate incomplete data collection.</p>"
                    html += "</div>"

                for section_key, section_data in domain_data.items():
                    if isinstance(section_data, dict) and not any(skip in section_key.lower() for skip in skip_sections):
                        section_name = section_data.get("name") or section_key.replace("_", " ").title()
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

                # Add sources/references section
                sources = domain_data.get("sources", [])
                if sources and len(sources) > 0:
                    html += f'<div class="subsection" style="page-break-inside: avoid; break-inside: avoid-column;">'
                    html += "<h4>📚 Sources & References</h4>"
                    for source in sources:
                        if isinstance(source, dict):
                            url = source.get("url", "")
                            title = source.get("title", "Unknown Source")
                            date = source.get("date", "")
                            snippet = source.get("snippet", "")

                            # Truncate very long URLs for PDF display (VertexAI grounding URLs can be 200+ chars)
                            display_url = url
                            if url and len(url) > 80:
                                # Show first 40 chars + ... + last 20 chars
                                display_url = url[:40] + "..." + url[-20:]

                            # Only show sources with meaningful content
                            if title and title != "Unknown Source":
                                distance_km = source.get("distance_from_site_km")
                                spatial_precision = source.get("spatial_precision", "")

                                html += f"<p style='margin: 2px 0; padding-left: 8px; border-left: 2px solid #1f77b4; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; max-width: 100%; line-height: 1.3;'>"
                                html += f"<strong style='word-break: break-word; font-size: 9px;'>{clean_markdown(title)}</strong>"
                                if date and date.strip():
                                    html += f"<br><em style='word-break: break-word; font-size: 8px;'>📅 {clean_markdown(date)}</em>"
                                if distance_km is not None:
                                    html += f"<br><span style='font-size: 7px; color: #1f77b4;'>📍 {distance_km} km from site</span>"
                                if spatial_precision and spatial_precision.strip():
                                    html += f"<br><span style='font-size: 7px; color: #666;'>🎯 {clean_markdown(spatial_precision)}</span>"
                                if display_url and display_url.strip():
                                    html += f"<br><span style='font-size: 7px; color: #666; word-break: break-all; overflow-wrap: anywhere; max-width: 100%;'>{clean_markdown(display_url)}</span>"
                                if snippet and snippet.strip():
                                    html += f"<br><em style='font-size: 8px; word-break: break-word; overflow-wrap: break-word;'>{clean_markdown(snippet)}</em>"
                                html += "</p>"
                        elif isinstance(source, str):
                            html += f"<p style='margin: 2px 0; padding-left: 10px; word-break: break-word; overflow-wrap: break-word; word-break: break-all; max-width: 100%;'>• {clean_markdown(source)}</p>"
                    html += "</div>"
                else:
                    # Show info message if no sources available
                    html += '<div class="subsection" style="background-color: #e7f3ff; padding: 10px; border-left: 3px solid #2196F3; margin: 10px 0;">'
                    html += "<p><strong>📚 Sources & References:</strong> No sources available - data collection pending</p>"
                    html += "</div>"

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

            # Ensure location_name is a string, not a dict or other object
            location_name_raw = raw_data.get('location', 'Unknown Location')
            if not isinstance(location_name_raw, str):
                location_name = str(location_name_raw) if location_name_raw else 'Unknown Location'
            else:
                location_name = location_name_raw

            # Sanitize location name to remove any dict/list repr artifacts
            import re
            location_name = re.sub(r'\{[^}]*\}', '', location_name)  # Remove {dict} artifacts
            location_name = location_name.strip()
            if not location_name:
                location_name = 'Unknown Location'

            # Generate HTML for PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Datacenter Analysis Report - {clean_markdown(location_name)}</title>
                <style>
                    @page {{ margin: 0.5in; size: A4; }}
                    body {{ font-family: Arial, sans-serif; font-size: 10px; line-height: 1.5; color: #333; margin: 0 auto; max-width: 100%; word-wrap: break-word; overflow-wrap: break-word; overflow-x: hidden; }}
                    .cover-page {{ text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 10px; margin-bottom: 25px; page-break-after: always; }}
                    .cover-title {{ font-size: 22px; font-weight: bold; color: #1f77b4; margin-bottom: 8px; }}
                    .cover-subtitle {{ font-size: 14px; color: #666; margin-bottom: 20px; }}
                    .cover-metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 15px 0; }}
                    .cover-metric {{ background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px; text-align: center; }}
                    .cover-metric-label {{ font-size: 9px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
                    .cover-metric-value {{ font-size: 16px; font-weight: bold; color: #1f77b4; }}
                    h1 {{ font-size: 16px; margin: 15px 0 10px 0; color: #1f77b4; page-break-after: avoid; }}
                    h2 {{ font-size: 14px; margin: 12px 0 8px 0; color: #333; page-break-after: avoid; }}
                    h3 {{ font-size: 12px; margin: 10px 0 6px 0; color: #666; page-break-after: avoid; }}
                    h4 {{ font-size: 11px; margin: 8px 0 4px 0; color: #666; page-break-after: avoid; }}
                    .section {{ margin: 20px 0; page-break-inside: avoid; clear: both; }}
                    .subsection {{ margin: 12px 0; page-break-inside: avoid; clear: both; }}
                    .domain-section {{ margin: 15px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #1f77b4; page-break-inside: avoid; }}
                    .metrics-container {{ margin: 10px 0; page-break-inside: avoid; clear: both; }}
                    .metrics-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9px; page-break-inside: avoid; position: relative; z-index: 1; table-layout: fixed; }}
                    .metrics-table th, .metrics-table td {{ border: 1px solid #dee2e6; padding: 5px 8px; text-align: left; vertical-align: top; background: white; word-wrap: break-word; overflow-wrap: break-word; }}
                    .metrics-table th {{ background: #f8f9fa; font-weight: bold; }}
                    .metrics-table th:first-child, .metrics-table td:first-child {{ width: 50%; }}
                    .metrics-table th:nth-child(2), .metrics-table td:nth-child(2) {{ width: 25%; }}
                    .metrics-table th:nth-child(3), .metrics-table td:nth-child(3) {{ width: 25%; }}
                    .metrics-table th:last-child, .metrics-table td:last-child {{ width: 20%; }}
                    .structured-section {{ page-break-inside: avoid; margin: 10px 0; clear: both; }}
                    ul, ol {{ margin: 8px 0; padding-left: 20px; max-width: 100%; }}
                    li {{ margin: 4px 0; line-height: 1.6; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; max-width: 100%; }}
                    p {{ margin: 6px 0; line-height: 1.6; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; max-width: 100%; }}
                    span {{ word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; }}
                    strong, em {{ word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; }}
                    div {{ word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; max-width: 100%; }}
                    a {{ word-wrap: break-word; overflow-wrap: break-word; word-break: break-all; }}
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

            # Investment-Grade Scoring Breakdown (PDF)
            weighted_scores_pdf = raw_data.get("weighted_domain_scores", [])
            all_caution_flags_pdf = raw_data.get("all_caution_flags", [])

            if weighted_scores_pdf:
                html_content += '<div class="section"><h2>📊 Investment-Grade Scoring Breakdown</h2>'

                # Add scoring explanation
                has_no_go_pdf = any(ws.get("no_go_gates_triggered", 0) > 0 for ws in weighted_scores_pdf)
                total_caution_penalty_pdf = sum(f.get("severity_points", 0) for f in all_caution_flags_pdf)

                if has_no_go_pdf:
                    html_content += '<div style="background: #fee; border-left: 4px solid #c00; padding: 12px; margin: 10px 0;">'
                    html_content += '<h3 style="color: #c00; margin-top: 0;">🚫 CRITICAL: NO-GO GATE TRIGGERED</h3>'
                    html_content += '<p><strong>Scoring Override:</strong> One or more critical failure conditions have been detected. When a NO-GO gate is triggered:</p>'
                    html_content += '<ul><li>All domain contributions are set to <strong>0.0</strong> (regardless of individual scores)</li>'
                    html_content += '<li>Final composite score becomes <strong>0.0/5.0</strong></li>'
                    html_content += '<li>Site is marked as <strong>NOT VIABLE</strong> for datacenter development</li></ul>'
                    html_content += '<p><strong>Critical failures must be resolved before proceeding with investment.</strong></p></div>'
                elif total_caution_penalty_pdf > 0:
                    html_content += '<div style="background: #ffc; border-left: 4px solid #f90; padding: 12px; margin: 10px 0;">'
                    html_content += f'<h3 style="color: #f90; margin-top: 0;">⚠️ Scoring Note: {len(all_caution_flags_pdf)} caution flags identified (-{total_caution_penalty_pdf:.2f} point penalty)</h3>'
                    html_content += '<p><strong>How scoring works:</strong></p><ol>'
                    html_content += '<li>Each domain contributes: <strong>Raw Score × Weight</strong> to the total</li>'
                    html_content += '<li>Caution flags apply penalty deductions based on severity</li>'
                    html_content += '<li>Final score = <strong>Weighted Sum - Penalties</strong> (minimum 1.0)</li></ol></div>'
                else:
                    html_content += '<div style="background: #efe; border-left: 4px solid #0a0; padding: 12px; margin: 10px 0;">'
                    html_content += '<p style="color: #0a0; margin: 0;"><strong>✅ Clean Analysis:</strong> No NO-GO gates triggered, no caution flags</p></div>'

                html_content += '<h3>Weighted Domain Contributions</h3>'
                html_content += '<table class="metrics-table" style="margin: 10px 0;">'
                html_content += '<tr><th>Domain</th><th>Raw Score</th><th>Weight</th><th>Contribution</th><th>NO-GO</th><th>Caution</th></tr>'

                total_weighted_pdf = 0
                for ws in weighted_scores_pdf:
                    domain = clean_markdown(ws.get("domain_name", "Unknown").replace("_", " ").title())
                    raw = ws.get("raw_score", 0)
                    weight = ws.get("weight", 0)
                    contrib = ws.get("weighted_contribution", 0)
                    no_go = ws.get("no_go_gates_triggered", 0)
                    caution = ws.get("caution_flags_count", 0)
                    total_weighted_pdf += contrib

                    html_content += f'<tr><td>{domain}</td><td>{raw:.2f}/5.0</td><td>{weight * 100:.0f}%</td><td>{contrib:.3f}</td><td>{no_go}</td><td>{caution}</td></tr>'

                html_content += '</table>'

                total_penalty_pdf = sum(f.get("severity_points", 0) for f in all_caution_flags_pdf)
                # Use actual composite score from data instead of recalculating
                # (synthesis agent applies additional logic like NO-GO overrides)

                html_content += '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">'
                html_content += f'<p><strong>Weighted Subtotal:</strong> {total_weighted_pdf:.2f}/5.0</p>'
                html_content += f'<p><strong>Caution Penalties:</strong> -{total_penalty_pdf:.2f} points</p>'
                html_content += f'<p><strong>Final Composite Score:</strong> {composite_score:.2f}/5.0</p>'
                html_content += '</div></div>'

            # NO-GO Gates (PDF)
            all_no_go_gates_pdf = raw_data.get("all_no_go_gates", [])

            if all_no_go_gates_pdf:
                triggered_pdf = [g for g in all_no_go_gates_pdf if g.get("triggered", False)]
                passed_pdf = [g for g in all_no_go_gates_pdf if not g.get("triggered", False)]

                html_content += '<div class="section"><h2>🚫 NO-GO Gate Analysis</h2>'
                html_content += f'<p><strong>Passed:</strong> {len(passed_pdf)} • <strong>Triggered:</strong> {len(triggered_pdf)}</p>'

                if triggered_pdf:
                    html_content += '<h3 style="color: #dc3545;">⛔ TRIGGERED NO-GO GATES</h3>'
                    for idx, gate in enumerate(triggered_pdf, 1):
                        html_content += f'<div style="background: #f8d7da; padding: 8px; border-left: 3px solid #dc3545; margin: 8px 0;">'
                        html_content += f'<h4>{idx}. {clean_markdown(gate.get("gate_type", "Unknown"))}</h4>'
                        html_content += f'<p><strong>Reason:</strong> {clean_markdown(gate.get("reason", "N/A"))}</p>'
                        if gate.get('standard_reference'):
                            html_content += f'<p><strong>Standard:</strong> {clean_markdown(gate.get("standard_reference"))}</p>'
                        if gate.get('mitigation_cost'):
                            html_content += f'<p><strong>Mitigation Cost:</strong> {clean_markdown(gate.get("mitigation_cost"))}</p>'
                        html_content += '</div>'

                if passed_pdf:
                    html_content += '<h3 style="color: #28a745;">✅ PASSED NO-GO GATES</h3>'
                    html_content += '<ul style="column-count: 2; font-size: 9px;">'
                    for gate in passed_pdf:
                        html_content += f'<li>{clean_markdown(gate.get("gate_type", "Unknown"))}</li>'
                    html_content += '</ul>'

                html_content += '</div>'

            # Caution Flags (PDF)
            if all_caution_flags_pdf:
                # Classify regional baseline vs independent flags for PDF
                regional_baseline_keywords_pdf = [
                    # Climate/Weather
                    'flood', 'coastal', 'temperature', 'humidity', 'wind', 'hurricane', 'storm',
                    'precipitation', 'climate', 'heat', 'cold', 'thermal', 'freezing', 'snow', 'ice',
                    'sea level', 'slr', 'storm surge', 'typhoon', 'cyclone',
                    # Infrastructure
                    'pile', 'foundation', 'soil', 'bearing', 'geotechnical', 'groundwater',
                    'drainage', 'freeboard', 'elevation', 'topography', 'grade', 'grading', 'fill',
                    'water', 'wastewater', 'water consumption', 'wue', 'cooling',
                    'transportation', 'highway', 'rail', 'road access', 'logistics',
                    # Energy/Efficiency
                    'pue', 'power', 'grid', 'utility', 'electrical',
                    # Regulatory
                    'permitting', 'permit', 'zoning', 'public hearing', 'cup', 'regulatory',
                    'compliance', 'municipal', 'county', 'local regulation'
                ]

                independent_hazard_keywords_pdf = [
                    # Site-specific hazards
                    'seismic', 'earthquake', 'liquefaction', 'wildfire', 'fire',
                    'tsunami', 'volcano', 'subsidence', 'karst', 'sinkhole',
                    'landslide', 'avalanche', 'tornado',
                    # Resource scarcity
                    'water stress', 'water scarcity', 'drought', 'aqueduct',
                    # Site-specific environmental
                    'contamination', 'endangered species', 'brownfield', 'hazmat', 'wetland',
                    'protected area', 'conservation',
                    # Business/market
                    'ixp', 'bandwidth', 'peering', 'demand', 'lease', 'market',
                    'data sovereignty', 'cloud act', 'lawful access',
                    # Design choices
                    'pue optimization', 'design choice'
                ]

                def is_regional_baseline_pdf(flag):
                    category_lower = flag.get('category', '').lower()
                    if any(keyword in category_lower for keyword in independent_hazard_keywords_pdf):
                        return False
                    return any(keyword in category_lower for keyword in regional_baseline_keywords_pdf)

                regional_flags_pdf = [f for f in all_caution_flags_pdf if is_regional_baseline_pdf(f)]
                independent_flags_pdf = [f for f in all_caution_flags_pdf if f not in regional_flags_pdf]
                regional_penalty_pdf = max([f.get('severity_points', 0.0) for f in regional_flags_pdf], default=0.0)
                independent_penalty_pdf = sum([f.get('severity_points', 0.0) for f in independent_flags_pdf])
                total_penalty_pdf = regional_penalty_pdf + independent_penalty_pdf

                high_pdf = [f for f in all_caution_flags_pdf if f.get("severity", "").lower() == "high"]
                medium_pdf = [f for f in all_caution_flags_pdf if f.get("severity", "").lower() == "medium"]
                low_pdf = [f for f in all_caution_flags_pdf if f.get("severity", "").lower() == "low"]

                html_content += '<div class="section"><h2>⚠️ Caution Flags & Risk Mitigation</h2>'
                html_content += f'<p><strong>Total Flags:</strong> {len(all_caution_flags_pdf)} ({len(regional_flags_pdf)} regional baseline, {len(independent_flags_pdf)} independent) • <strong>Total Penalty:</strong> -{total_penalty_pdf:.2f} points</p>'
                if regional_flags_pdf:
                    html_content += f'<p style="font-size: 9px; background: #e3f2fd; padding: 5px; border-radius: 3px;">🌍 <strong>Penalty Breakdown:</strong> Regional baseline flags: -{regional_penalty_pdf:.2f} (max applied, not stacked) | Independent hazards: -{independent_penalty_pdf:.2f} (summed)</p>'

                if high_pdf:
                    high_pen = sum(f.get("severity_points", 0) for f in high_pdf)
                    html_content += f'<h3 style="color: #dc3545;">🔴 HIGH SEVERITY ({len(high_pdf)} flags, -{high_pen:.2f} penalty)</h3>'
                    for idx, flag in enumerate(high_pdf, 1):
                        is_regional_pdf = is_regional_baseline_pdf(flag)
                        regional_badge_pdf = "🌍 Regional" if is_regional_pdf else "⚠️ Independent"
                        html_content += '<div style="background: #f8d7da; padding: 6px; margin: 4px 0; border-left: 2px solid #dc3545;">'
                        html_content += f'<p><strong>{idx}. {clean_markdown(flag.get("category", "Unknown"))} ({regional_badge_pdf}, Penalty: -{flag.get("severity_points", 0):.2f})</strong></p>'
                        html_content += f'<p style="font-size: 9px;"><strong>Issue:</strong> {clean_markdown(flag.get("description", "N/A"))}</p>'
                        html_content += f'<p style="font-size: 9px;"><strong>Mitigation:</strong> {clean_markdown(flag.get("mitigation_plan", "TBD"))}</p>'
                        if flag.get('cost_impact'):
                            html_content += f'<p style="font-size: 8px;"><strong>Cost:</strong> {clean_markdown(flag.get("cost_impact"))}</p>'
                        if flag.get('timeline_impact'):
                            html_content += f'<p style="font-size: 8px;"><strong>Timeline:</strong> {clean_markdown(flag.get("timeline_impact"))}</p>'
                        html_content += '</div>'

                if medium_pdf:
                    medium_pen = sum(f.get("severity_points", 0) for f in medium_pdf)
                    html_content += f'<h3 style="color: #ffc107;">🟡 MEDIUM SEVERITY ({len(medium_pdf)} flags, -{medium_pen:.2f} penalty)</h3>'
                    for idx, flag in enumerate(medium_pdf, 1):
                        is_regional_pdf = is_regional_baseline_pdf(flag)
                        regional_icon_pdf = "🌍" if is_regional_pdf else "⚠️"
                        html_content += '<div style="background: #fff3cd; padding: 6px; margin: 4px 0; border-left: 2px solid #ffc107;">'
                        html_content += f'<p style="font-size: 9px;"><strong>{regional_icon_pdf} {idx}. {clean_markdown(flag.get("category", "Unknown"))} (Penalty: -{flag.get("severity_points", 0):.2f})</strong></p>'
                        html_content += f'<p style="font-size: 9px;">{clean_markdown(flag.get("description", "N/A"))}</p>'
                        html_content += f'<p style="font-size: 9px;"><em>Mitigation: {clean_markdown(flag.get("mitigation_plan", "TBD"))}</em></p>'
                        if flag.get('cost_impact'):
                            html_content += f'<p style="font-size: 8px;">Cost: {clean_markdown(flag.get("cost_impact"))}</p>'
                        html_content += '</div>'

                if low_pdf:
                    low_pen = sum(f.get("severity_points", 0) for f in low_pdf)
                    html_content += f'<h3 style="color: #28a745;">🟢 LOW SEVERITY ({len(low_pdf)} flags, -{low_pen:.2f} penalty)</h3>'
                    for idx, flag in enumerate(low_pdf, 1):
                        is_regional_pdf = is_regional_baseline_pdf(flag)
                        regional_icon_pdf = "🌍" if is_regional_pdf else "⚠️"
                        html_content += f'<p style="font-size: 8px;"><strong>{regional_icon_pdf} {idx}. {clean_markdown(flag.get("category", "Unknown"))} (-{flag.get("severity_points", 0):.2f}):</strong> {clean_markdown(flag.get("description", "N/A"))}</p>'

                html_content += '</div>'

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

            # Sanitize html_content to remove any stray Python dict representations
            # Pattern matches: {'key': 'value', ...} anywhere in the HTML
            html_content = re.sub(r'\{[\'"]category[\'"]:.*?\}', '', html_content, flags=re.DOTALL)

            # Generate PDF using xhtml2pdf (pure Python, cross-platform)
            pdf_buffer = io.BytesIO()
            pisa_status = pisa.CreatePDF(
                src=html_content,
                dest=pdf_buffer,
                encoding='utf-8'
            )
            pdf_buffer.seek(0)

            if pisa_status.err:
                raise Exception(f"PDF generation failed with {pisa_status.err} errors")

            # Download button
            st.download_button(
                label="💾 Download PDF Report",
                data=pdf_buffer.getvalue(),
                file_name=f"datacenter_report_{raw_data.get('location', 'unknown').replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
            st.success("📄 PDF generated successfully!")

        except ImportError:
            st.error("📄 PDF generation requires xhtml2pdf. Install with: uv add xhtml2pdf or pip install xhtml2pdf")
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
            st.info("💡 Please ensure xhtml2pdf is installed: uv add xhtml2pdf")