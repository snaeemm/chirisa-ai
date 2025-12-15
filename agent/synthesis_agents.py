# synthesis_agents.py - Synthesis and Report Orchestration

import os
import asyncio
from dotenv import load_dotenv
from google.adk.tools import FunctionTool
import json_repair
from .models import (
    ReportSchema, LocationContext, AgentOutput, NoGoGate, CautionFlag,
    ProvenanceBadge, WeightedDomainScore
)
from .database import save_report_to_database
from .domain_models import (
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    SiteCivilInfrastructureOutput, MechanicalThermalOutput,
    RegulatoryESGOutput, MarketCompetitionOutput
)
from .utility import save_report_schema
from typing import Dict, List, Any, Tuple

# Load environment variables from .env file
load_dotenv(override=True)

# Configuration
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# ================================================================================================
# INVESTMENT-GRADE COMPOSITE SCORING (Chirisa-AI)
# ================================================================================================

# Domain weights based on investment-grade specifications
DOMAIN_WEIGHTS = {
    "power_energy": 0.35,           # Power availability & interconnection (critical constraint)
    "network_connectivity": 0.15,    # Connectivity & on-ramps
    "site_civil": 0.10,              # Site & civil (parcel, access, logistics, drainage)
    "hazards_resilience": 0.12,      # Hazards & resilience (flood, seismic, wildfire, wind, extremes)
    "mechanical_thermal": 0.08,      # Mechanical & thermal (cooling/PUE/water treatment)
    "regulatory_esg": 0.14,          # Regulatory & ESG (zoning, permits, incentives, trajectory)
    "market_competition": 0.06,      # Market depth & competition
}

def calculate_weighted_composite_score(
    agent_results: Dict[str, Any]
) -> Tuple[float, List[WeightedDomainScore], List[NoGoGate], List[CautionFlag]]:
    """
    Calculate investment-grade weighted composite score with NO-GO gate checks.

    Returns:
        Tuple of (composite_score, weighted_scores, all_no_go_gates, all_caution_flags)
        - composite_score: 0.0 if NO-GO triggered, otherwise weighted 1.0-5.0
        - weighted_scores: List of WeightedDomainScore objects
        - all_no_go_gates: Aggregated NO-GO gates from all domains
        - all_caution_flags: Aggregated caution flags from all domains
    """

    # Step 1: Extract domain scores and check for NO-GO gates
    domain_scores = {
        "power_energy": getattr(agent_results.get('power_result'), 'overall_score', 1.0),
        "network_connectivity": getattr(agent_results.get('network_result'), 'overall_score', 1.0),
        "site_civil": getattr(agent_results.get('site_civil_result'), 'overall_score', 1.0),
        "hazards_resilience": getattr(agent_results.get('climate_result'), 'overall_score', 1.0),
        "mechanical_thermal": getattr(agent_results.get('mechanical_thermal_result'), 'overall_score', 1.0),
        "regulatory_esg": getattr(agent_results.get('regulatory_esg_result'), 'overall_score', 1.0),  # MERGED regulatory + ESG domain (14% weight)
        "market_competition": getattr(agent_results.get('market_competition_result'), 'overall_score', 1.0),
    }

    # Step 2: Collect NO-GO gates and caution flags from all domains
    all_no_go_gates = []
    all_caution_flags = []
    no_go_counts = {}
    caution_counts = {}

    for domain_key, result_key in [
        ("power_energy", 'power_result'),
        ("network_connectivity", 'network_result'),
        ("site_civil", 'site_civil_result'),
        ("hazards_resilience", 'climate_result'),
        ("mechanical_thermal", 'mechanical_thermal_result'),
        ("regulatory_esg", 'regulatory_esg_result'),  # MERGED regulatory + ESG domain (14% weight)
        ("market_competition", 'market_competition_result')
    ]:
        if result_key not in agent_results:
            no_go_counts[domain_key] = 0
            caution_counts[domain_key] = 0
            continue

        result = agent_results[result_key]

        # Extract NO-GO gates if present and tag with domain
        no_go_gates = getattr(result, 'no_go_gates', [])
        if no_go_gates:
            # Tag each gate with its source domain for better logging
            for gate in no_go_gates:
                if not hasattr(gate, '_source_domain'):
                    gate._source_domain = domain_key
            all_no_go_gates.extend(no_go_gates)
        no_go_counts[domain_key] = len([g for g in no_go_gates if getattr(g, 'triggered', False)])

        # Extract caution flags if present
        caution_flags = getattr(result, 'caution_flags', [])
        if caution_flags:
            all_caution_flags.extend(caution_flags)
        caution_counts[domain_key] = len(caution_flags)

    # Step 3: Check for triggered NO-GO gates (hard stop)
    triggered_no_go_gates = [g for g in all_no_go_gates if getattr(g, 'triggered', False)]
    if triggered_no_go_gates:
        print(f"🚫 NO-GO TRIGGERED: {len(triggered_no_go_gates)} gate(s) failed - Composite score overridden to 0.0")
        for gate in triggered_no_go_gates:
            domain_name = getattr(gate, '_source_domain', 'Unknown Domain')
            # Format domain name for readability
            formatted_domain = domain_name.replace('_', ' ').title()
            print(f"   - [{formatted_domain}] {gate.gate_type}: {gate.reason}")

        # Return 0.0 composite score with weighted breakdown
        weighted_scores = [
            WeightedDomainScore(
                domain_name=domain,
                raw_score=max(1.0, min(5.0, score)),  # Clamp to valid range
                weight=DOMAIN_WEIGHTS[domain],
                weighted_contribution=0.0,  # Zero contribution due to NO-GO
                no_go_gates_triggered=no_go_counts.get(domain, 0),
                caution_flags_count=caution_counts.get(domain, 0)
            )
            for domain, score in domain_scores.items()
        ]

        return 0.0, weighted_scores, all_no_go_gates, all_caution_flags

    # Step 4: Calculate weighted composite score
    weighted_sum = 0.0
    weighted_scores = []

    for domain, score in domain_scores.items():
        weight = DOMAIN_WEIGHTS[domain]
        # Clamp score to valid range
        clamped_score = max(1.0, min(5.0, score if score > 0 else 2.5))
        weighted_contribution = clamped_score * weight
        weighted_sum += weighted_contribution

        weighted_scores.append(WeightedDomainScore(
            domain_name=domain,
            raw_score=clamped_score,
            weight=weight,
            weighted_contribution=weighted_contribution,
            no_go_gates_triggered=no_go_counts.get(domain, 0),
            caution_flags_count=caution_counts.get(domain, 0)
        ))

    # Step 5: Apply caution flag penalties with anti-stacking for regional baseline adjustments
    # Regional baseline flags (coastal, climate, foundations) share geography-based risks
    # and should not stack excessively. Independent hazards (seismic, wildfire) stack normally.

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

    # Independent hazard keywords - these should NOT be classified as regional baseline
    independent_hazard_keywords = [
        # Site-specific hazards (not geography-based)
        'seismic', 'earthquake', 'liquefaction', 'wildfire', 'fire',
        'tsunami', 'volcano', 'subsidence', 'karst', 'sinkhole',
        'landslide', 'avalanche', 'tornado',

        # Resource scarcity (site-specific, not regional norm)
        'water stress', 'water scarcity', 'drought', 'aqueduct',

        # Site-specific environmental
        'contamination', 'endangered species', 'brownfield', 'hazmat', 'wetland',
        'protected area', 'conservation',

        # Business/market (not geography-based)
        'ixp', 'bandwidth', 'peering', 'demand', 'lease', 'market',
        'data sovereignty', 'cloud act', 'lawful access',

        # Design choices (not baseline)
        'pue optimization', 'design choice'
    ]

    def is_regional_baseline(flag):
        category_lower = getattr(flag, 'category', '').lower()
        # Exclude if it's an independent hazard
        if any(keyword in category_lower for keyword in independent_hazard_keywords):
            return False
        # Include if it's a regional baseline factor
        return any(keyword in category_lower for keyword in regional_baseline_keywords)

    regional_baseline_flags = [f for f in all_caution_flags if is_regional_baseline(f)]
    independent_flags = [f for f in all_caution_flags if f not in regional_baseline_flags]

    # Regional baseline: Take MAX penalty (don't stack coastal + wind + foundation for same geography)
    regional_penalty = max(
        [getattr(f, 'severity_points', 0.0) for f in regional_baseline_flags],
        default=0.0
    )

    # Independent hazards: Sum normally (seismic + wildfire should stack as they're independent risks)
    independent_penalty = sum(
        [getattr(f, 'severity_points', 0.0) for f in independent_flags]
    )

    total_caution_penalty = regional_penalty + independent_penalty

    # Apply penalty cap: Cannot drop more than 50% below weighted sum
    # This prevents composite collapse when category scores are solid (3.5+)
    capped_penalty = min(total_caution_penalty, weighted_sum * 0.5)
    final_composite = max(1.0, weighted_sum - capped_penalty)

    print(f"📊 Weighted Composite Score: {final_composite:.2f}/5.0")
    print(f"   Base Weighted Sum: {weighted_sum:.2f}")
    print(f"   Regional Baseline Penalty: -{regional_penalty:.2f} (max of {len(regional_baseline_flags)} flags)")
    print(f"   Independent Hazards Penalty: -{independent_penalty:.2f} (sum of {len(independent_flags)} flags)")
    print(f"   Total Penalty: -{total_caution_penalty:.2f}")
    if capped_penalty < total_caution_penalty:
        print(f"   ⚠️  Penalty Capped: -{capped_penalty:.2f} (50% of base score cap applied)")
    else:
        print(f"   Applied Penalty: -{capped_penalty:.2f}")
    print(f"⚠️  Caution Flags: {len(all_caution_flags)} total ({len(regional_baseline_flags)} regional, {len(independent_flags)} independent)")

    return final_composite, weighted_scores, all_no_go_gates, all_caution_flags

# --------------------------------------------------------------------------------
# Simplified Response Handling - Agents now output structured JSON directly
# --------------------------------------------------------------------------------

def clean_agent_response(response_text: str) -> str:
    """Remove markdown code block wrapper from agent response and ensure English text"""
    import re

    cleaned = response_text.strip()

    # Check for empty or whitespace-only response
    if not cleaned:
        return cleaned

    # Remove ```json from start (case insensitive)
    if cleaned.lower().startswith('```json'):
        cleaned = cleaned[7:]  # Remove '```json'
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]   # Remove '```' only

    # Remove ``` from end
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]

    # Clean and ensure proper encoding
    cleaned = cleaned.strip()

    # Pre-process problematic escape sequences before JSON parsing
    # Replace common problematic patterns that don't need escaping in JSON
    cleaned = cleaned.replace('\\$', '$')  # Dollar signs
    cleaned = cleaned.replace('\\%', '%')  # Percent signs
    cleaned = cleaned.replace('\\&', '&')  # Ampersands
    cleaned = cleaned.replace('\\#', '#')  # Hash symbols
    cleaned = cleaned.replace('\\-', '-')  # Hyphens
    cleaned = cleaned.replace('\\+', '+')  # Plus signs
    cleaned = cleaned.replace('\\=', '=')  # Equal signs
    cleaned = cleaned.replace('\\*', '*')  # Asterisks
    cleaned = cleaned.replace('\\(', '(')  # Open parenthesis
    cleaned = cleaned.replace('\\)', ')')  # Close parenthesis
    cleaned = cleaned.replace('\\[', '[')  # Open bracket (but be careful!)
    cleaned = cleaned.replace('\\]', ']')  # Close bracket (but be careful!)
    cleaned = cleaned.replace('\\<', '<')  # Less than
    cleaned = cleaned.replace('\\>', '>')  # Greater than
    cleaned = cleaned.replace('\\:', ':')  # Colons
    cleaned = cleaned.replace('\\;', ';')  # Semicolons
    cleaned = cleaned.replace('\\_', '_')  # Underscores

    # Remove any non-printable characters that could cause black boxes
    cleaned = re.sub(r'[^\x20-\x7E\n\r\t]', '', cleaned)

    # Ensure proper UTF-8 encoding
    try:
        cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
    except Exception:
        pass

    return cleaned

def repair_json_response(json_text: str) -> str:
    """
    Repair JSON using json-repair library.
    This replaces 100+ lines of fragile regex with a battle-tested library.
    """
    import re

    # Remove any text before the first {
    start_idx = json_text.find('{')
    if start_idx > 0:
        json_text = json_text[start_idx:]

    # Remove any text after the last }
    end_idx = json_text.rfind('}')
    if end_idx >= 0:
        json_text = json_text[:end_idx + 1]

    # Use json-repair library to fix all JSON issues
    # It handles: escape sequences, missing commas, trailing commas,
    # malformed strings, Python booleans/None, missing quotes, and more
    return json_repair.repair_json(json_text)

def extract_grounding_sources(response) -> list:
    """Extract grounding sources (web search results) from Gemini API response"""
    grounding_sources = []
    try:

        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]

            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding_metadata = candidate.grounding_metadata

                # Check if grounding_chunks exists and has items
                chunks = getattr(grounding_metadata, 'grounding_chunks', None)

                # Try grounding_supports first (newer API structure)
                if hasattr(grounding_metadata, 'grounding_supports') and grounding_metadata.grounding_supports:
                    supports = grounding_metadata.grounding_supports
                    for i, support in enumerate(supports):

                        # Try to extract from segment or grounding_chunk_indices
                        if hasattr(support, 'segment'):
                            segment = support.segment

                        if hasattr(support, 'grounding_chunk_indices') and support.grounding_chunk_indices:
                            chunk_indices = support.grounding_chunk_indices

                            # Now look up those chunks from grounding_chunks
                            if hasattr(grounding_metadata, 'grounding_chunks') and grounding_metadata.grounding_chunks:
                                for idx in chunk_indices:
                                    if idx < len(grounding_metadata.grounding_chunks):
                                        chunk = grounding_metadata.grounding_chunks[idx]

                                        if hasattr(chunk, 'web') and chunk.web:
                                            url = chunk.web.uri if hasattr(chunk.web, 'uri') and chunk.web.uri else ""
                                            title = chunk.web.title if hasattr(chunk.web, 'title') and chunk.web.title else "Web Source"

                                            source = {
                                                "url": str(url) if url else "",
                                                "title": str(title) if title else "Web Source",
                                                "date": "",
                                                "snippet": ""
                                            }
                                            if source["url"]:
                                                grounding_sources.append(source)

                # Also try direct grounding_chunks (older API structure)
                elif hasattr(grounding_metadata, 'grounding_chunks') and grounding_metadata.grounding_chunks:
                    for i, chunk in enumerate(grounding_metadata.grounding_chunks):
                        if hasattr(chunk, 'web') and chunk.web:
                            url = chunk.web.uri if hasattr(chunk.web, 'uri') and chunk.web.uri else ""
                            title = chunk.web.title if hasattr(chunk.web, 'title') and chunk.web.title else "Web Source"

                            source = {
                                "url": str(url) if url else "",
                                "title": str(title) if title else "Web Source",
                                "date": "",
                                "snippet": ""
                            }
                            if source["url"]:
                                grounding_sources.append(source)
                else:
                    # No grounding sources found in metadata
                    pass
            else:
                print(f"⚠️ No grounding_metadata in candidate")
        else:
            print(f"⚠️ No candidates in response")

    except Exception as e:
        print(f"❌ ERROR extracting grounding metadata: {e}")

    return grounding_sources

def normalize_pydantic_response(data: dict) -> dict:
    """
    Normalize LLM JSON responses to match Pydantic model requirements:
    - Convert capitalized literals to lowercase (High -> high, Medium -> medium)
    - Map invalid severity values (Extreme -> high, medium-high -> medium)
    - Fix field name mismatches
    - Handle invalid escape sequences
    - Normalize sub_scores (clamp to 1.0-5.0, preserve -1.0 for failures)
    - Convert string fields to lists/dicts where needed
    - Clean confidence values with parenthetical notes
    """
    if not isinstance(data, dict):
        return data

    # Fix top-level field type mismatches FIRST
    if 'third_party_verification' in data and isinstance(data['third_party_verification'], str):
        data['third_party_verification'] = [data['third_party_verification']]

    if 'data_gaps' in data and isinstance(data['data_gaps'], str):
        data['data_gaps'] = [data['data_gaps']]

    if 'phase_1_recommendations' in data:
        if isinstance(data['phase_1_recommendations'], list):
            recommendations = {}
            for i, item in enumerate(data['phase_1_recommendations'], 1):
                recommendations[f"priority_{i}"] = item
            data['phase_1_recommendations'] = recommendations
        elif isinstance(data['phase_1_recommendations'], str):
            data['phase_1_recommendations'] = {"priority_1": data['phase_1_recommendations']}

    # Convert string arrays to empty lists for no_go_gates, caution_flags, provenance_badges
    if 'no_go_gates' in data and isinstance(data['no_go_gates'], list):
        data['no_go_gates'] = [item for item in data['no_go_gates'] if isinstance(item, dict)]

    if 'caution_flags' in data and isinstance(data['caution_flags'], list):
        data['caution_flags'] = [item for item in data['caution_flags'] if isinstance(item, dict)]

    if 'provenance_badges' in data and isinstance(data['provenance_badges'], list):
        data['provenance_badges'] = [item for item in data['provenance_badges'] if isinstance(item, dict)]

    # FIX: Validate RichSection fields - convert lists/empty dicts to None
    # RichSection fields that should be dicts or None (not lists)
    rich_section_fields = [
        # Site & Civil Infrastructure
        'land_availability', 'geotechnical_conditions', 'water_wastewater',
        'transportation_access', 'permitting_timeline', 'civil_grading',
        # Mechanical & Thermal
        'cooling_strategy', 'hvac_design', 'thermal_resilience',
        'free_cooling_efficiency', 'water_consumption', 'mechanical_infrastructure',
        'fire_suppression',
        # Market & Competition
        'market_size', 'demand_drivers', 'competitive_landscape',
        'pricing_dynamics', 'market_maturity', 'entry_barriers',
        'growth_outlook'
    ]

    for field in rich_section_fields:
        if field in data:
            # If it's a list or empty dict, set to None
            if isinstance(data[field], list):
                print(f"⚠️ Converting RichSection field '{field}' from list to None")
                data[field] = None
            elif isinstance(data[field], dict) and len(data[field]) == 0:
                print(f"⚠️ Converting RichSection field '{field}' from empty dict to None")
                data[field] = None
            elif isinstance(data[field], dict):
                # Ensure it has at least a 'name' field to be valid RichSection
                if 'name' not in data[field]:
                    data[field]['name'] = field.replace('_', ' ').title()

    # FIX: Validate and clamp overall_score to valid range (1.0-5.0)
    # This prevents Pydantic validation errors when LLM returns 0.0 or other invalid values
    if 'overall_score' in data:
        score = data['overall_score']
        if isinstance(score, (int, float)):
            if score < 1.0:
                print(f"⚠️ Clamping overall_score from {score} to 1.0 (minimum)")
                data['overall_score'] = 1.0
            elif score > 5.0:
                print(f"⚠️ Clamping overall_score from {score} to 5.0 (maximum)")
                data['overall_score'] = 5.0
        elif score is None:
            print(f"⚠️ Converting None overall_score to 1.0 (default)")
            data['overall_score'] = 1.0
        else:
            # Try to convert string to float
            try:
                data['overall_score'] = float(score)
                if data['overall_score'] < 1.0:
                    data['overall_score'] = 1.0
                elif data['overall_score'] > 5.0:
                    data['overall_score'] = 5.0
            except (ValueError, TypeError):
                print(f"⚠️ Invalid overall_score '{score}', defaulting to 1.0")
                data['overall_score'] = 1.0

    normalized = {}

    for key, value in data.items():
        # Normalize lists recursively
        if isinstance(value, list):
            normalized[key] = [normalize_pydantic_response(item) if isinstance(item, dict) else item for item in value]

            # Fix specific field issues in list items
            if key in ['caution_flags', 'no_go_gates']:
                for item in normalized[key]:
                    if isinstance(item, dict):
                        # Normalize severity/confidence literals to lowercase and map invalid values
                        if 'severity' in item and isinstance(item['severity'], str):
                            import re
                            severity_str = item['severity']
                            # Strip parenthetical notes like "(long-term)", "(short-term)", etc.
                            severity_clean = re.sub(r'\s*\([^)]*\)', '', severity_str).strip()
                            severity_lower = severity_clean.lower()
                            # Map invalid severity values to valid ones
                            if severity_lower in ['extreme', 'critical', 'very high', 'very_high']:
                                item['severity'] = 'high'
                            elif severity_lower in ['moderate', 'medium-high', 'medium-low', 'med']:
                                item['severity'] = 'medium'
                            elif severity_lower in ['very low', 'very_low', 'minimal']:
                                item['severity'] = 'low'
                            elif severity_lower in ['high', 'medium', 'low']:
                                item['severity'] = severity_lower
                            else:
                                # Fallback to medium if we can't determine
                                item['severity'] = 'medium'

                        if 'confidence' in item and isinstance(item['confidence'], str):
                            confidence_lower = item['confidence'].lower()
                            # Map invalid confidence values to valid ones
                            if confidence_lower in ['very high', 'very_high', 'excellent']:
                                item['confidence'] = 'high'
                            elif confidence_lower in ['moderate', 'fair']:
                                item['confidence'] = 'medium'
                            elif confidence_lower in ['very low', 'very_low', 'poor']:
                                item['confidence'] = 'low'
                            else:
                                item['confidence'] = confidence_lower

                        # Fix CautionFlag field names (old: flag_type/mitigation, new: category/mitigation_plan)
                        if 'flag_type' in item:
                            item['category'] = item.pop('flag_type')
                        if 'mitigation' in item and 'mitigation_plan' not in item:
                            item['mitigation_plan'] = item.pop('mitigation')

                        # Fix mitigation_possible boolean parsing (for no_go_gates)
                        if key == 'no_go_gates' and 'mitigation_possible' in item:
                            if isinstance(item['mitigation_possible'], str):
                                mitigation_str = item['mitigation_possible'].lower().strip()
                                # Map string booleans to actual booleans
                                if mitigation_str in ['true', 'yes', 'y', '1', 'possible']:
                                    item['mitigation_possible'] = True
                                elif mitigation_str in ['false', 'no', 'n', '0', 'not possible', 'not applicable', 'n/a', 'na']:
                                    item['mitigation_possible'] = False
                                else:
                                    # Default to True if ambiguous
                                    item['mitigation_possible'] = True

                        # Ensure required fields have defaults if missing
                        if key == 'caution_flags':
                            if 'description' not in item and 'category' in item:
                                item['description'] = item.get('category', 'No description provided')
                            if 'cost_impact' not in item:
                                item['cost_impact'] = 'To be determined'
                            if 'mitigation_plan' not in item:
                                item['mitigation_plan'] = 'Requires further analysis'

                            # Add missing severity field
                            if 'severity' not in item:
                                # Infer from severity_points if available
                                if 'severity_points' in item:
                                    sp = item['severity_points']
                                    if isinstance(sp, (int, float)):
                                        if sp >= 0.7:
                                            item['severity'] = 'high'
                                        elif sp >= 0.4:
                                            item['severity'] = 'medium'
                                        else:
                                            item['severity'] = 'low'
                                    else:
                                        item['severity'] = 'medium'
                                else:
                                    item['severity'] = 'medium'  # Default

                            # Fix severity_points - must be <= 1.0 (it's a score deduction)
                            if 'severity_points' in item:
                                severity_points = item['severity_points']
                                if isinstance(severity_points, (int, float)):
                                    # If value is > 1, it's likely on wrong scale (e.g., 3 instead of 0.3)
                                    if severity_points > 1.0:
                                        item['severity_points'] = min(severity_points / 10.0, 1.0)
                                    # Ensure it's at least 0.1 and at most 1.0
                                    item['severity_points'] = max(0.1, min(item['severity_points'], 1.0))

            elif key == 'provenance_badges':
                for item in normalized[key]:
                    if isinstance(item, dict):
                        # Normalize confidence to lowercase and strip parenthetical notes
                        if 'confidence' in item and isinstance(item['confidence'], str):
                            import re
                            confidence_str = item['confidence']
                            # Strip parenthetical notes like "(proxy)", "(estimated distance)", etc.
                            confidence_clean = re.sub(r'\s*\([^)]*\)', '', confidence_str).strip()
                            confidence_lower = confidence_clean.lower()

                            if confidence_lower in ['very high', 'very_high', 'excellent']:
                                item['confidence'] = 'high'
                            elif confidence_lower in ['moderate', 'fair', 'med']:  # Added 'med'
                                item['confidence'] = 'medium'
                            elif confidence_lower in ['very low', 'very_low', 'poor']:
                                item['confidence'] = 'low'
                            elif confidence_lower in ['high', 'medium', 'low']:
                                item['confidence'] = confidence_lower
                            else:
                                # Fallback to 'medium' if we can't determine
                                item['confidence'] = 'medium'
                        # Fix field name issues - convert old source_name to source
                        if 'source_name' in item and 'source' not in item:
                            item['source'] = item.pop('source_name')
                        # Add missing required fields with defaults if needed
                        if 'vintage' not in item:
                            item['vintage'] = 'recent'
                        if 'coverage' not in item:
                            item['coverage'] = 'partial'

            elif key == 'distance_measurements':
                for item in normalized[key]:
                    if isinstance(item, dict):
                        # Normalize method to valid enum values
                        if 'method' in item and isinstance(item['method'], str):
                            method = item['method'].lower()
                            # Map invalid methods to valid ones (more comprehensive)
                            if 'road' in method or 'approximate' in method or 'driving' in method or 'ground' in method:
                                item['method'] = 'road'
                            elif 'aerial' in method or 'direct' in method or 'proximity' in method or 'air' in method or 'straight' in method or 'line' in method:
                                item['method'] = 'aerial'
                            elif 'rail' in method or 'train' in method:
                                item['method'] = 'rail'
                            elif 'fiber' in method or 'cable' in method:
                                item['method'] = 'fiber_route'
                            else:
                                item['method'] = 'road'  # Default fallback
                        # Fix field name: from_location -> source, to_location -> target, destination -> target
                        if 'from_location' in item and 'source' not in item:
                            item['source'] = item.pop('from_location')
                        if 'to_location' in item and 'target' not in item:
                            item['target'] = item.pop('to_location')
                        if 'destination' in item and 'target' not in item:
                            item['target'] = item.pop('destination')
                        # Also check for 'location' as a target field
                        if 'location' in item and 'target' not in item:
                            item['target'] = item.pop('location')
                        # Ensure required fields exist with defaults
                        if 'target' not in item:
                            # Check if there's a name field that could be used
                            item['target'] = item.get('name', item.get('facility_name', 'Unknown Location'))
                        if 'distance_km' not in item and 'distance' in item:
                            # Try to extract distance_km from generic 'distance' field
                            item['distance_km'] = item.pop('distance')
                        if 'distance_km' not in item or item['distance_km'] is None:
                            item['distance_km'] = 0.0
                        # Ensure distance_km is a valid float, not None or string
                        if item['distance_km'] is None:
                            item['distance_km'] = 0.0
                        # Fix string distance_km values like "< 1.0", "~25.0", "~320.0"
                        if 'distance_km' in item and isinstance(item['distance_km'], str):
                            import re
                            # Extract numbers from strings like "< 1.0" or "~25.0"
                            numbers = re.findall(r'\d+\.?\d*', item['distance_km'])
                            if numbers:
                                item['distance_km'] = float(numbers[0])
                            else:
                                item['distance_km'] = 0.0

                        # Fix routing_buffer - must be float or None, not string
                        if 'routing_buffer' in item:
                            if isinstance(item['routing_buffer'], str):
                                # Try to extract a number from the string
                                import re
                                numbers = re.findall(r'\d+\.?\d*', item['routing_buffer'])
                                if numbers:
                                    try:
                                        item['routing_buffer'] = float(numbers[0])
                                    except ValueError:
                                        item['routing_buffer'] = None
                                else:
                                    # No number found, set to None
                                    item['routing_buffer'] = None
                            elif not isinstance(item['routing_buffer'], (int, float, type(None))):
                                item['routing_buffer'] = None

            # Normalize sections (RichSection models)
            elif key == 'sections' or key.endswith('_sections'):
                for item in normalized[key]:
                    if isinstance(item, dict):
                        # Normalize sub_score: preserve -1.0 for failures, clamp others to 1.0-5.0
                        if 'sub_score' in item:
                            sub_score = item['sub_score']
                            if isinstance(sub_score, (int, float)):
                                if sub_score != -1.0:  # Preserve -1.0 for failures
                                    if sub_score < 1.0:
                                        item['sub_score'] = 1.0  # Clamp to minimum
                                    elif sub_score > 5.0:
                                        item['sub_score'] = 5.0  # Clamp to maximum

        # Normalize nested dicts recursively
        elif isinstance(value, dict):
            normalized[key] = normalize_pydantic_response(value)

            # Handle sections as dict (not list) - some models use Dict[str, RichSection]
            if key == 'sections' or key.endswith('_sections'):
                for section_key, section_data in normalized[key].items():
                    if isinstance(section_data, dict) and 'sub_score' in section_data:
                        sub_score = section_data['sub_score']
                        if isinstance(sub_score, (int, float)):
                            if sub_score != -1.0:  # Preserve -1.0 for failures
                                if sub_score < 1.0:
                                    section_data['sub_score'] = 1.0  # Clamp to minimum
                                elif sub_score > 5.0:
                                    section_data['sub_score'] = 5.0  # Clamp to maximum
        else:
            normalized[key] = value

    # FINAL PASS: Fix severity_points globally in any caution_flags
    # This catches caution_flags at any level (top-level or nested)
    if 'caution_flags' in normalized and isinstance(normalized['caution_flags'], list):
        for flag in normalized['caution_flags']:
            if isinstance(flag, dict) and 'severity_points' in flag:
                severity_points = flag['severity_points']
                if isinstance(severity_points, (int, float)) and severity_points > 1.0:
                    flag['severity_points'] = min(severity_points / 10.0, 1.0)
                    flag['severity_points'] = max(0.1, min(flag['severity_points'], 1.0))

    return normalized


def sanitize_sources(sources: list) -> list:
    """Sanitize sources list to ensure all fields are valid strings"""
    if not isinstance(sources, list):
        return []

    sanitized = []
    for source in sources:
        if isinstance(source, dict):
            # Ensure all required fields are present and are strings (not None)
            sanitized_source = {
                "url": str(source.get("url", "")) if source.get("url") is not None else "",
                "title": str(source.get("title", "Unknown Source")) if source.get("title") is not None else "Unknown Source",
                "date": str(source.get("date", "")) if source.get("date") is not None else "",
                "snippet": str(source.get("snippet", "")) if source.get("snippet") is not None else ""
            }
            # Only add if we have at least a URL
            if sanitized_source["url"]:
                sanitized.append(sanitized_source)
        elif isinstance(source, str):
            # If source is just a string, create a minimal source object
            sanitized.append({
                "url": "",
                "title": str(source),
                "date": "",
                "snippet": ""
            })

    return sanitized

def backfill_source_names_in_verification_metadata(response_data: dict) -> dict:
    """
    Backfill source names for verification_metadata entries that only have level strings.

    When LLM outputs verification_metadata as "verified_by_public_source" (string) instead of
    {"level": "verified_by_public_source", "source": "EIA.gov 2024"} (dict), this function
    tries to find the source name from the sources array and convert to dict format.
    """
    if not isinstance(response_data, dict):
        return response_data

    sources = response_data.get("sources", [])
    if not sources or not isinstance(sources, list):
        return response_data

    # Extract source titles for matching (e.g., "EIA.gov", "World Bank", etc.)
    source_titles = []
    for source in sources:
        if isinstance(source, dict) and "title" in source:
            title = source["title"]
            date = source.get("date", "")
            source_titles.append((title, date))

    # Process all subsections
    for key, value in response_data.items():
        if isinstance(value, dict) and "verification_metadata" in value:
            verification_metadata = value["verification_metadata"]
            if not isinstance(verification_metadata, dict):
                continue

            updated_metadata = {}
            for metric_key, verification_value in verification_metadata.items():
                # If it's already a dict, keep it
                if isinstance(verification_value, dict):
                    updated_metadata[metric_key] = verification_value
                # If it's "verified_by_public_source" string, try to find source name
                elif verification_value == "verified_by_public_source":
                    # Try to find a matching source from sources array
                    # Strategy: Use the first source (most relevant) or try to match by keywords
                    if source_titles:
                        # Use first source as default
                        title, date = source_titles[0]
                        # Simple heuristic: extract source name (e.g., "EIA.gov Electric Power" -> "EIA.gov")
                        source_name_parts = title.split(" ")
                        source_name = source_name_parts[0] if source_name_parts else title
                        if date and date != "Unknown":
                            source_name = f"{source_name} {date}"

                        updated_metadata[metric_key] = {
                            "level": "verified_by_public_source",
                            "source": source_name
                        }
                    else:
                        # No sources available, keep as string
                        updated_metadata[metric_key] = verification_value
                else:
                    # Other levels (verified_by_osm, model_inference, etc.) keep as string
                    updated_metadata[metric_key] = verification_value

            value["verification_metadata"] = updated_metadata

    return response_data


def sanitize_metrics_data(data: dict) -> dict:
    """Sanitize metrics data to ensure all percentages and numerical values are valid numbers"""
    import re

    def clean_number_string(value):
        """Convert string representations to numbers, handling special cases"""
        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):
            # Remove any non-numeric characters except decimal point, minus sign, and digits
            cleaned = re.sub(r'[^\d.\-]', '', value.strip())

            # If we have an empty string after cleaning, return 0
            if not cleaned or cleaned == '-':
                return 0

            try:
                # Try to parse as float first, then convert to int if it's a whole number
                num = float(cleaned)
                if num == int(num):
                    return int(num)
                return num
            except ValueError:
                return 0

        return 0

    # Recursively process the data structure
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key in ['percentages', 'numerical_values']:
                # These should contain numeric values
                if isinstance(value, dict):
                    sanitized[key] = {k: clean_number_string(v) for k, v in value.items()}
                else:
                    sanitized[key] = value
            elif key == 'metrics' and isinstance(value, dict):
                # Recursively sanitize metrics
                sanitized[key] = sanitize_metrics_data(value)
            elif isinstance(value, dict):
                # Recursively process nested dicts
                sanitized[key] = sanitize_metrics_data(value)
            elif isinstance(value, list):
                # Process lists
                sanitized[key] = [sanitize_metrics_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized

    return data

def detect_json_error_type(error_message: str, response_text: str) -> str:
    """Detect specific type of JSON error for targeted retry instructions"""
    error_msg = str(error_message).lower()

    if "control character" in error_msg:
        return "control_character"
    elif "expecting" in error_msg and ("," in error_msg or "}" in error_msg or "]" in error_msg):
        return "syntax_error"
    elif "unterminated string" in error_msg:
        return "unterminated_string"
    elif "expecting property name" in error_msg:
        return "missing_quotes"
    elif "trailing comma" in error_msg:
        return "trailing_comma"
    elif len(response_text.strip()) == 0:
        return "empty_response"
    else:
        return "general_formatting"

def robust_json_parse(response_text: str, description: str = "response") -> dict:
    """Parse JSON with multiple repair attempts and detailed logging"""
    import json

    print(f"🔍 Parsing {description}...")

    # Step 0: Check for empty response
    if not response_text or not response_text.strip():
        print(f"❌ Empty response received for {description}")
        raise json.JSONDecodeError("Empty response", response_text or "", 0)

    # Step 1: Basic cleaning
    cleaned = clean_agent_response(response_text)
    print(f"📝 Cleaned response length: {len(cleaned)} characters")

    # Step 1.5: Check if cleaned response is empty
    if not cleaned or not cleaned.strip():
        print(f"❌ Response became empty after cleaning for {description}")
        raise json.JSONDecodeError("Empty response after cleaning", cleaned, 0)

    # Step 2: Try direct parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        error_type = detect_json_error_type(str(e), cleaned)
        print(f"⚠️ Initial JSON parse failed: {e} (Type: {error_type})")
        print(f"📄 Raw response preview: {cleaned[:500]}...")

    # Step 3: Enhanced repair based on error type
    try:
        repaired = repair_json_response(cleaned)
        print(f"🔧 Attempted JSON repair...")
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        print(f"❌ Repaired JSON parse failed: {e}")
        print(f"📄 Repaired preview: {repaired[:500]}...")

    # Step 4: Control character specific cleaning
    try:
        import re
        # Remove control characters more aggressively
        control_char_cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', cleaned)
        if control_char_cleaned != cleaned:
            print(f"🧹 Attempting control character removal...")
            return json.loads(control_char_cleaned)
    except json.JSONDecodeError as e:
        print(f"❌ Control character cleaning failed: {e}")

    # Step 5: Try extracting just the JSON object
    try:
        import re
        # Look for the main JSON object pattern
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            json_only = json_match.group()
            repaired_only = repair_json_response(json_only)
            return json.loads(repaired_only)
    except Exception as e:
        print(f"❌ JSON extraction failed: {e}")

    # If all else fails, raise the original error with context and error type
    original_error = json.JSONDecodeError(f"Failed to parse {description} after all repair attempts", cleaned, 0)
    original_error.error_type = error_type  # Add error type for retry logic
    raise original_error

# --------------------------------------------------------------------------------
# Agent Retry Mechanism for JSON Parsing Failures
# --------------------------------------------------------------------------------

async def call_agent_with_retry(agent_wrapper, method_name: str, lat: float, lng: float, country: str, context=None, max_retries: int = 2):
    """Intelligent retry wrapper for agent calls that handles JSON parsing failures"""
    import json

    for attempt in range(max_retries + 1):
        try:
            print(f"🚀 Calling {agent_wrapper.name} (attempt {attempt + 1}/{max_retries + 1})")

            # Call the agent method
            method = getattr(agent_wrapper, method_name)
            result = await method(lat, lng, country, context)

            # If we get here, the call was successful
            print(f"✅ {agent_wrapper.name} completed successfully on attempt {attempt + 1}")
            return result

        except json.JSONDecodeError as json_error:
            error_type = getattr(json_error, 'error_type', 'unknown')
            print(f"❌ {agent_wrapper.name} JSON parsing failed on attempt {attempt + 1}: {json_error}")
            print(f"🔍 Error type detected: {error_type}")

            # If this was the last attempt, fall back to error response
            if attempt >= max_retries:
                print(f"🛑 Max retries ({max_retries}) reached for {agent_wrapper.name}, using fallback response")
                return create_fallback_response(agent_wrapper.name, lat, lng, country, str(json_error))

            # Prepare retry with enhanced instructions based on error type
            print(f"🔄 Preparing retry {attempt + 2} for {agent_wrapper.name} with enhanced JSON instructions...")

            # Modify the agent's instruction temporarily for retry
            original_instruction = agent_wrapper.adk_agent.instruction
            enhanced_instruction = create_enhanced_json_instruction(original_instruction, error_type, attempt + 1)
            agent_wrapper.adk_agent.instruction = enhanced_instruction

            # Wait a bit before retrying (exponential backoff)
            retry_delay = 2 ** attempt  # 1s, 2s, 4s...
            print(f"⏱️ Waiting {retry_delay}s before retry...")
            await asyncio.sleep(retry_delay)

        except Exception as general_error:
            print(f"❌ {agent_wrapper.name} failed with non-JSON error on attempt {attempt + 1}: {general_error}")

            # For non-JSON errors, don't retry - return fallback immediately
            return create_fallback_response(agent_wrapper.name, lat, lng, country, str(general_error))

    # This shouldn't be reached, but just in case
    return create_fallback_response(agent_wrapper.name, lat, lng, country, "Maximum retries exceeded")

def create_enhanced_json_instruction(original_instruction: str, error_type: str, attempt: int) -> str:
    """Create enhanced instruction with specific JSON formatting guidance based on error type"""

    error_specific_guidance = {
        "control_character": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Remove ALL control characters, special symbols, and non-printable characters
- Use only standard ASCII characters (letters, numbers, basic punctuation)
- No smart quotes, em-dashes, or special Unicode characters
- Ensure all text is clean, readable English without formatting artifacts""",

        "syntax_error": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Double-check all JSON syntax: proper commas, brackets, braces
- Ensure every opening brace {{ has a closing brace }}
- Ensure every opening bracket [ has a closing bracket ]
- No trailing commas before closing braces or brackets""",

        "unterminated_string": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Ensure ALL string values are properly quoted with double quotes
- Escape any internal quotes with backslashes: "He said \\"Hello\\""
- Close all string values properly - no missing closing quotes""",

        "missing_quotes": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- ALL property names must be in double quotes: "property_name"
- ALL string values must be in double quotes: "string_value"
- Use only double quotes, never single quotes in JSON""",

        "trailing_comma": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Remove ALL trailing commas before closing braces or brackets
- Last item in objects or arrays should NOT have a comma after it""",

        "empty_response": """
CRITICAL RESPONSE REQUIREMENTS (Retry #{attempt}):
- Provide a complete JSON response - do not return empty content
- Include all required fields according to the schema
- Ensure the response contains actual analysis data""",

        "general_formatting": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Response must be valid JSON format with proper structure
- Use proper JSON syntax with double quotes for strings
- Remove any markdown formatting (```json, ```)
- Ensure clean, parseable JSON structure"""
    }

    guidance = error_specific_guidance.get(error_type, error_specific_guidance["general_formatting"])
    guidance = guidance.replace("{attempt}", str(attempt))

    enhanced_instruction = f"""{original_instruction}

{guidance}

IMPORTANT: Your previous response had a JSON formatting error ({error_type}). Please provide the same high-quality analysis but ensure perfect JSON formatting. Focus on providing the same valuable insights with corrected formatting."""

    return enhanced_instruction

def create_fallback_response(agent_name: str, lat: float, lng: float, country: str, error_message: str):
    """Create a fallback AgentOutput when all retry attempts fail"""
    from .models import AgentOutput

    return AgentOutput(
        overall_score=2.5,  # Neutral score since we couldn't get real analysis
        sections={},
        assumptions=[f"Analysis generated using fallback due to technical issue: {error_message[:100]}..."],
        key_insights=[f"Data center analysis for {country} requires further investigation due to processing error"],
        executive_summary=f"Technical analysis for {lat}, {lng} in {country} encountered processing issues. Manual review recommended for comprehensive assessment."
    )

# --------------------------------------------------------------------------------
# OSM Power Infrastructure Integration Helpers
# --------------------------------------------------------------------------------

def format_osm_for_prompt(osm_data: dict) -> str:
    """Format OSM infrastructure data for LLM prompt"""
    if not osm_data or not osm_data.get("nearest_substation_name"):
        return """
## OpenInfraMap Ground Truth: NO SUBSTATIONS FOUND
⚠️ WARNING: OpenStreetMap/OpenInfraMap found NO transmission substations within 100km search radius.
This indicates either:
1. Remote location with limited transmission infrastructure
2. Incomplete mapping in OpenStreetMap (common in some regions)
3. Genuine infrastructure gap

**REQUIRED ACTION**: Flag this as a CautionFlag with high severity for infrastructure availability.
"""

    # Format substation info
    sub_name = osm_data["nearest_substation_name"]
    latin = osm_data.get("latin_name", "N/A")
    voltages = osm_data.get("substation_voltages_kV", [])
    voltage_str = "/".join([f"{int(v)}" if v.is_integer() else f"{v}" for v in voltages]) if voltages else "Unknown"
    dist = osm_data.get("substation_distance_km", "?")
    voltage_src = osm_data.get("voltage_source", "unknown")
    last_updated = osm_data.get("substation_last_updated", "Unknown")

    # Format transmission lines
    lines = osm_data.get("nearest_lines", [])
    lines_text = ""
    if lines:
        for i, line in enumerate(lines[:3], 1):
            line_v = line.get("voltage_kV", [])
            line_v_str = "/".join([f"{int(v)}" if v.is_integer() else f"{v}" for v in line_v])
            circuits = line.get("circuit_count")
            circ_str = f" ({circuits} circuits)" if circuits else ""
            lines_text += f"  {i}. {line['name']}: {line_v_str} kV{circ_str} at {line['distance_km']} km (updated: {line.get('last_updated', 'Unknown')})\n"
    else:
        lines_text = "  None found with voltage data\n"

    # Build complete context
    return f"""
## OpenInfraMap Ground Truth Data (Verified Infrastructure)
**Source**: OpenStreetMap/OpenInfraMap via Overpass API
**Search Radius**: {osm_data.get('search_radius_km', '?')} km
**Data Vintage**: {last_updated}
**Note**: Grid topology based on OpenStreetMap as of {last_updated[:10] if last_updated != 'Unknown' else 'last available update'} — recent grid expansions or upgrades may not yet be reflected in OSM data.

### Nearest Substation
- **Name**: {sub_name} (Latin: {latin})
- **Voltages**: {voltage_str} kV (Source: {voltage_src})
- **Distance**: {dist} km from site
- **Last Updated**: {last_updated}

### Transmission Lines (≥69 kV)
{lines_text}

**CRITICAL INSTRUCTIONS FOR USING THIS DATA:**
1. **Substation Distance**: Use the OSM-verified distance ({dist} km) as ground truth in your power_capacity analysis and MENTION it in your content text
2. **Voltage Verification**: Tag substation voltages as "verified_by_osm" in verification_metadata (NOT verified_by_public_source)
3. **Cross-Validation**: If you find different substation distances from web search, FLAG the discrepancy
4. **Capacity vs Infrastructure**: Remember - OSM shows INFRASTRUCTURE presence, NOT available capacity (capacity = "unknown_requires_utility_letter")
5. **Data Quality**: {'Voltage data missing in OSM - note as data gap' if voltage_src == 'not_available_in_osm' else 'Voltage confirmed from OSM tags - tag as verified_by_osm'}
6. **Distance Measurements**: Add this to your distance_measurements array with source="OpenInfraMap"
7. **Reference in Text**: In your power_capacity content, write something like: "OpenInfraMap confirms a {voltage_str} kV substation at {dist} km from the site."
8. **Add to Metrics**: Include these values in power_capacity.metrics.numerical_values with appropriate units
"""


def enrich_power_output_with_osm(response_data: dict, osm_data: dict) -> dict:
    """Post-process LLM output to inject OSM-derived structured data"""
    if not osm_data or not osm_data.get("nearest_substation_name"):
        return response_data

    # 1. Add OSM to sources
    if "sources" not in response_data:
        response_data["sources"] = []

    osm_source = {
        "url": f"https://openinframap.org/#9/{osm_data.get('substation_distance_km', 0)}/power",
        "title": "OpenInfraMap - Open Power Infrastructure Database",
        "date": osm_data.get("last_updated", "Unknown"),
        "snippet": f"Nearest substation: {osm_data['nearest_substation_name']} at {osm_data.get('substation_distance_km')} km"
    }
    response_data["sources"].append(osm_source)

    # 2. Add distance measurements
    if "distance_measurements" not in response_data:
        response_data["distance_measurements"] = []

    # Substation distance
    voltages = osm_data.get("substation_voltages_kV", [])
    voltage_str = "/".join([f"{int(v)}" if v.is_integer() else f"{v}" for v in voltages]) + " kV" if voltages else ""

    response_data["distance_measurements"].append({
        "target": f"{osm_data['nearest_substation_name']} ({voltage_str})".strip(),
        "distance_km": osm_data.get("substation_distance_km", 0),
        "distance_mi": round(osm_data.get("substation_distance_km", 0) * 0.621371, 2),
        "method": "aerial",
        "source": "OpenInfraMap"
    })

    # Transmission line distances
    for line in osm_data.get("nearest_lines", [])[:3]:
        line_v = line.get("voltage_kV", [])
        line_v_str = "/".join([f"{int(v)}" if v.is_integer() else f"{v}" for v in line_v]) + " kV"
        response_data["distance_measurements"].append({
            "target": f"{line['name']} ({line_v_str})",
            "distance_km": line["distance_km"],
            "distance_mi": round(line["distance_km"] * 0.621371, 2),
            "method": "aerial",
            "source": "OpenInfraMap"
        })

    # 3. Add provenance badge
    if "provenance_badges" not in response_data:
        response_data["provenance_badges"] = []

    response_data["provenance_badges"].append({
        "source": "OpenStreetMap / OpenInfraMap",
        "api_version": "Overpass API 0.7",
        "vintage": osm_data.get("last_updated", "Unknown"),
        "refresh_frequency": "Continuous (community-updated)",
        "confidence": "high" if osm_data.get("voltage_source") == "osm_tag" else "medium",
        "coverage": "HV/EHV transmission substations and lines ≥69 kV",
        "url": "https://openinframap.org"
    })

    # 4. Enhance power_capacity metrics (if section exists)
    if "power_capacity" in response_data and isinstance(response_data["power_capacity"], dict):
        capacity_section = response_data["power_capacity"]
        if "metrics" not in capacity_section:
            capacity_section["metrics"] = {
                "numerical_values": {},
                "percentages": {},
                "ranges": {},
                "units": {}
            }

        # Add OSM-derived metrics
        metrics = capacity_section["metrics"]
        metrics["numerical_values"]["osm_nearest_substation_distance_km"] = osm_data.get("substation_distance_km", 0)
        metrics["units"]["osm_nearest_substation_distance_km"] = "km"

        if voltages:
            metrics["numerical_values"]["osm_substation_max_voltage_kv"] = max(voltages)
            metrics["units"]["osm_substation_max_voltage_kv"] = "kV"

        # Add voltage source clarification to key_points
        if "key_points" not in capacity_section:
            capacity_section["key_points"] = []

        voltage_src = osm_data.get("voltage_source", "unknown")
        if voltage_src == "osm_tag":
            capacity_section["key_points"].append(
                "Substation voltage confirmed from OpenStreetMap infrastructure tags (verified by OSM)"
            )
        elif voltage_src == "not_available_in_osm":
            capacity_section["key_points"].append(
                "Substation voltage data unavailable in OpenStreetMap — voltage confirmation requires utility schematic"
            )

        line_count = len(osm_data.get("nearest_lines", []))
        if line_count > 0:
            metrics["numerical_values"]["osm_transmission_lines_nearby"] = line_count
            metrics["units"]["osm_transmission_lines_nearby"] = "count"

    # 5. Update verification_metadata to include source names with dates (match PeeringDB format)
    osm_last_updated = osm_data.get("last_updated", "Unknown")
    if osm_last_updated == "Unknown":
        osm_source_name = "OpenInfraMap"
    else:
        # Use parentheses format: "OpenInfraMap (2024-12-08)"
        date_str = osm_last_updated[:10] if len(osm_last_updated) > 10 else osm_last_updated
        osm_source_name = f"OpenInfraMap ({date_str})"

    # Add verification_metadata for OSM-derived metrics in power_capacity
    if "power_capacity" in response_data and isinstance(response_data["power_capacity"], dict):
        capacity_section = response_data["power_capacity"]
        if "verification_metadata" not in capacity_section:
            capacity_section["verification_metadata"] = {}

        # Add source attribution for OSM metrics
        osm_metrics = ["osm_nearest_substation_distance_km", "osm_substation_max_voltage_kv", "osm_transmission_lines_nearby"]
        for metric_key in osm_metrics:
            if metric_key in capacity_section.get("metrics", {}).get("numerical_values", {}):
                capacity_section["verification_metadata"][metric_key] = {
                    "level": "verified_by_osm",
                    "source": osm_source_name
                }

    return response_data


def detect_osm_llm_conflicts(response_data: dict, osm_data: dict) -> dict:
    """Detect conflicts between OSM ground truth and LLM findings, generate CautionFlags"""
    if not osm_data:
        return response_data

    if "caution_flags" not in response_data:
        response_data["caution_flags"] = []

    # CONFLICT 1: No substations found in OSM
    if not osm_data.get("nearest_substation_name"):
        response_data["caution_flags"].append({
            "category": "infrastructure_availability",
            "severity": "high",
            "description": f"OpenInfraMap found NO transmission substations within {osm_data.get('search_radius_km', 100)} km search radius",
            "mitigation_plan": "Verify with regional grid operator if infrastructure exists but is unmapped in OSM. May require extended transmission line construction.",
            "cost_impact": "Potentially +$5-15M for extended transmission infrastructure if no nearby substations confirmed",
            "timeline_impact": "+12-24 months for transmission line construction and utility approvals",
            "severity_points": 0.8
        })

    # CONFLICT 2: Missing voltage data in OSM
    if osm_data.get("voltage_source") == "not_available_in_osm" and osm_data.get("nearest_substation_name"):
        if "data_gaps" not in response_data:
            response_data["data_gaps"] = []
        response_data["data_gaps"].append(
            "OSM substation voltage data unavailable - requires utility schematic or site visit for voltage confirmation"
        )

    # CONFLICT 3: Distance discrepancy (compare OSM vs LLM metrics)
    osm_dist = osm_data.get("substation_distance_km")
    if osm_dist and "power_capacity" in response_data:
        capacity = response_data.get("power_capacity", {})
        if isinstance(capacity, dict) and "metrics" in capacity:
            metrics = capacity["metrics"]
            numerical = metrics.get("numerical_values", {})

            # Look for LLM-estimated substation distance
            llm_dist_keys = ["substation_distance_km", "nearest_substation_km", "distance_to_substation_km"]
            for key in llm_dist_keys:
                if key in numerical:
                    llm_dist = numerical[key]
                    if isinstance(llm_dist, (int, float)):
                        diff = abs(llm_dist - osm_dist)
                        pct_diff = (diff / osm_dist) * 100 if osm_dist > 0 else 0

                        if diff > 5 and pct_diff > 50:  # >5km AND >50% difference
                            response_data["caution_flags"].append({
                                "category": "data_quality",
                                "severity": "medium",
                                "description": f"Substation distance discrepancy: LLM estimate {llm_dist} km vs OSM ground truth {osm_dist} km (difference: {diff:.1f} km)",
                                "mitigation_plan": f"Use OpenInfraMap distance ({osm_dist} km) as more reliable. Verify with site survey and utility maps.",
                                "cost_impact": "No direct cost impact, but affects infrastructure routing planning",
                                "timeline_impact": None,
                                "severity_points": 0.2
                            })
                            break

    # CONFLICT 4: Voltage discrepancy
    osm_voltages = osm_data.get("substation_voltages_kV", [])
    if osm_voltages and "power_capacity" in response_data:
        capacity = response_data.get("power_capacity", {})
        if isinstance(capacity, dict) and "metrics" in capacity:
            metrics = capacity["metrics"]
            numerical = metrics.get("numerical_values", {})

            # Look for LLM-estimated voltage
            llm_voltage_keys = ["transmission_voltage_kv", "max_transmission_voltage_kv", "grid_voltage_kv"]
            for key in llm_voltage_keys:
                if key in numerical:
                    llm_voltage = numerical[key]
                    osm_max_voltage = max(osm_voltages)
                    if isinstance(llm_voltage, (int, float)):
                        diff = abs(llm_voltage - osm_max_voltage)

                        if diff > 10:  # >10 kV difference is significant
                            response_data["caution_flags"].append({
                                "category": "data_quality",
                                "severity": "high",
                                "description": f"Substation voltage discrepancy: LLM estimate {llm_voltage} kV vs OSM {osm_max_voltage} kV (difference: {diff} kV). Voltage affects transformer specifications.",
                                "mitigation_plan": f"Use OpenInfraMap voltage ({osm_max_voltage} kV) as baseline. Confirm with utility grid schematic before equipment procurement.",
                                "cost_impact": "Transformer specifications depend on voltage - incorrect estimates may require re-procurement (+$500K-2M)",
                                "timeline_impact": "+3-6 months if equipment re-procurement needed",
                                "severity_points": 0.5
                            })
                            break

    # CONFLICT 5: Old OSM data warning
    last_updated = osm_data.get("last_updated", "Unknown")
    if last_updated != "Unknown":
        try:
            from datetime import datetime
            update_date = datetime.strptime(last_updated, "%Y-%m-%d")
            age_years = (datetime.now() - update_date).days / 365.25

            if age_years > 2:
                if "assumptions" not in response_data:
                    response_data["assumptions"] = []
                response_data["assumptions"].append(
                    f"OpenInfraMap data last updated {last_updated} ({age_years:.1f} years ago) - may not reflect recent grid expansions or upgrades"
                )
        except Exception:
            pass

    return response_data


# ---- Network API Helper Functions (PeeringDB) ----

def format_peeringdb_for_prompt(peeringdb_data: dict) -> str:
    """Format PeeringDB infrastructure data for LLM prompt"""
    if not peeringdb_data:
        return """
## PeeringDB Ground Truth: API QUERY FAILED
⚠️ WARNING: PeeringDB API query failed or returned no data.
This may indicate network connectivity issues or PeeringDB service disruption.

**REQUIRED ACTION**: Note this as a data gap. Rely on web search for network infrastructure.
"""

    facilities = peeringdb_data.get("facilities", [])
    ixps = peeringdb_data.get("ixps", [])
    carriers = peeringdb_data.get("carriers", [])
    last_updated = peeringdb_data.get("last_updated", "Unknown")

    # Check if no infrastructure found
    if not facilities and not ixps:
        return """
## PeeringDB Ground Truth: NO NETWORK INFRASTRUCTURE FOUND
⚠️ WARNING: PeeringDB found NO colocation facilities or Internet Exchange Points within 200 km search radius.
This indicates either:
1. Remote location with limited network infrastructure
2. Incomplete mapping in PeeringDB (less common for major metro areas)
3. Genuine infrastructure gap requiring extensive fiber builds

**REQUIRED ACTION**: Flag this as a CautionFlag with high severity for infrastructure_availability.
"""

    # Format facilities
    fac_text = ""
    if facilities:
        fac_text = "### Colocation Facilities (within 200 km)\n"
        for i, fac in enumerate(facilities[:5], 1):
            operator = fac.get("operator", "Unknown Operator")
            city = fac.get("city", "Unknown")
            country = fac.get("country", "")
            dist = fac.get("distance_km", "?")
            method = fac.get("distance_method", "unknown")
            quality_flags = fac.get("data_quality_flag", [])
            flag_str = f" ⚠️ Data Quality Issues: {', '.join(quality_flags)}" if quality_flags else ""
            fac_text += f"  {i}. **{fac['name']}** (Operator: {operator})\n"
            fac_text += f"     Location: {city}, {country} | Distance: {dist} km ({method}){flag_str}\n"
    else:
        fac_text = "### Colocation Facilities\n  None found within 200 km\n"

    # Format IXPs
    ixp_text = ""
    if ixps:
        ixp_text = "### Internet Exchange Points (within 500 km)\n"
        for i, ixp in enumerate(ixps[:3], 1):
            city = ixp.get("city", "Unknown")
            country = ixp.get("country", "")
            dist = ixp.get("distance_km", "?")
            asn_count = ixp.get("asn_count")
            asn_str = f"{asn_count} networks" if asn_count else "ASN count unknown"
            ixp_type = ixp.get("ixp_type", "unknown")
            quality_flags = ixp.get("data_quality_flag", [])
            flag_str = f" ⚠️ Data Quality Issues: {', '.join(quality_flags)}" if quality_flags else ""
            ixp_text += f"  {i}. **{ixp['name']}** ({asn_str})\n"
            ixp_text += f"     Location: {city}, {country} | Distance: {dist} km | Type: {ixp_type}{flag_str}\n"
    else:
        ixp_text = "### Internet Exchange Points\n  None found within 500 km\n"

    # Format carriers
    carrier_text = ""
    if carriers:
        carrier_text = f"### Network Carriers Present ({len(carriers)} carriers)\n"
        carrier_text += "  " + ", ".join(carriers[:15])
        if len(carriers) > 15:
            carrier_text += f" ... and {len(carriers) - 15} more"
        carrier_text += "\n"
    else:
        carrier_text = "### Network Carriers\n  None identified in facilities\n"

    # Build complete context
    return f"""
## PeeringDB Ground Truth Data (Verified Infrastructure)
**Source**: PeeringDB - Global Network Infrastructure Database
**Data Vintage**: {last_updated if last_updated != "Unknown" else "Not available"}

{fac_text}
{ixp_text}
{carrier_text}

**CRITICAL INSTRUCTIONS FOR USING THIS DATA:**
1. **Facility Distances**: Use PeeringDB-verified distances as ground truth for fiber_infrastructure and last_mile_diversity
2. **IXP Verification**: Tag IXP data as "verified_by_peeringdb" in verification_metadata
3. **Carrier Diversity**: Use carrier list for carrier_diversity analysis - tag as "verified_by_peeringdb"
4. **Cross-Validation**: If web search finds different facilities/distances, FLAG the discrepancy
5. **Data Quality Flags**: Pay attention to data_quality_flag warnings (suspect coordinates, distributed locations)
6. **Distance Measurements**: Add all facilities and IXPs to distance_measurements array with source="PeeringDB"
7. **No Facilities Warning**: If PeeringDB returns "NO FACILITIES FOUND", add high-severity CautionFlag for infrastructure_availability
8. **IXP Types**:
   - "domestic" = same country
   - "regional_cross_border" = different country but ≤500 km
   - "international" = different country and >500 km

**PEERINGDB VERIFICATION TAGGING:**
- Facility existence: "verified_by_peeringdb" (if found in PeeringDB)
- IXP existence: "verified_by_peeringdb" (if found in PeeringDB)
- Carrier presence: "verified_by_peeringdb" (if in PeeringDB carrier list)
- Distance measurements: "verified_by_peeringdb" (from PeeringDB coordinates)
- Latency estimates: "model_inference" (PeeringDB doesn't provide latency)
- Bandwidth costs: "unknown_requires_isp_quote" (PeeringDB doesn't show pricing)
"""


def enrich_network_output_with_peeringdb(response_data: dict, peeringdb_data: dict) -> dict:
    """Post-process LLM output to inject PeeringDB-derived structured data"""
    if not peeringdb_data:
        return response_data

    facilities = peeringdb_data.get("facilities", [])
    ixps = peeringdb_data.get("ixps", [])
    carriers = peeringdb_data.get("carriers", [])
    last_updated = peeringdb_data.get("last_updated", "Unknown")

    # Parse last_updated timestamp to display format
    formatted_date = "Unknown"
    if last_updated and last_updated != "Unknown":
        try:
            from datetime import datetime
            # PeeringDB returns ISO format: "2024-12-08T10:30:00Z"
            dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%Y-%m-%d")
        except Exception:
            formatted_date = last_updated[:10] if len(last_updated) >= 10 else last_updated

    # 1. Add PeeringDB to sources
    if "sources" not in response_data:
        response_data["sources"] = []

    peeringdb_source = {
        "url": "https://www.peeringdb.com/",
        "title": "PeeringDB - Global Network Infrastructure Database",
        "date": last_updated if last_updated != "Unknown" else "Unknown",
        "snippet": f"Found {len(facilities)} facilities, {len(ixps)} IXPs, {len(carriers)} carriers"
    }
    response_data["sources"].append(peeringdb_source)

    # 2. Add distance measurements
    if "distance_measurements" not in response_data:
        response_data["distance_measurements"] = []

    # Clean up existing LLM-generated distance measurements (Fixes 1 & 3)
    for measurement in response_data.get("distance_measurements", []):
        # Fix missing miles conversion
        if measurement.get("distance_mi") is None and measurement.get("distance_km"):
            measurement["distance_mi"] = round(measurement["distance_km"] * 0.621371, 2)

        # Fix "Unknown" targets
        if measurement.get("target") == "Unknown" or not measurement.get("target"):
            source = measurement.get("source", "")
            km = measurement.get("distance_km", "?")
            measurement["target"] = f"Unspecified location ({source} reference)"

        # Fix method labeling for aerial + routing buffer
        if measurement.get("method") == "road":
            source = measurement.get("source", "")
            if source in ["Google Maps", "Model Estimate"] and measurement.get("routing_buffer") is None:
                measurement["method"] = "aerial"
                measurement["routing_buffer"] = 30.0
                measurement["source"] = "Model Estimate"

    # Facility distances
    for fac in facilities[:5]:
        response_data["distance_measurements"].append({
            "target": f"{fac['name']} (Colo Facility)",
            "distance_km": fac.get("distance_km", 0),
            "distance_mi": round(fac.get("distance_km", 0) * 0.621371, 2),
            "method": "aerial",
            "source": "PeeringDB",
            "data_quality_flag": fac.get("data_quality_flag", [])
        })

    # IXP distances
    for ixp in ixps[:3]:
        ixp_type_label = {
            "domestic": "Domestic IXP",
            "regional_cross_border": "Regional IXP",
            "international": "International IXP"
        }.get(ixp.get("ixp_type", "domestic"), "IXP")

        response_data["distance_measurements"].append({
            "target": f"{ixp['name']} ({ixp_type_label})",
            "distance_km": ixp.get("distance_km", 0),
            "distance_mi": round(ixp.get("distance_km", 0) * 0.621371, 2),
            "method": "aerial",
            "source": "PeeringDB",
            "data_quality_flag": ixp.get("data_quality_flag", [])
        })

    # 3. Add provenance badge
    if "provenance_badges" not in response_data:
        response_data["provenance_badges"] = []

    # Add fetch_date for clarity (Fix 12)
    from datetime import datetime
    fetch_date = datetime.now().strftime("%Y-%m-%d")

    response_data["provenance_badges"].append({
        "source": "PeeringDB",
        "api_version": "PeeringDB API 2.0",
        "vintage": last_updated if last_updated != "Unknown" else "Unknown",
        "fetch_date": fetch_date,  # When we queried the API
        "refresh_frequency": "Community-updated (real-time)",
        "confidence": "high" if (facilities or ixps) else "low",
        "coverage": f"{len(facilities)} facilities, {len(ixps)} IXPs, {len(carriers)} carriers within search radius",
        "url": "https://www.peeringdb.com"
    })

    # 4. Enhance network subsection metrics (if sections exist)
    # Add PeeringDB-derived metrics to relevant subsections
    subsection_enhancements = {
        "fiber_infrastructure": {
            "peeringdb_facilities_within_200km": len(facilities),
        },
        "ixp_peering": {
            "peeringdb_ixps_within_500km": len(ixps),
            "peeringdb_nearest_ixp_distance_km": ixps[0]["distance_km"] if ixps else None,
            "peeringdb_nearest_ixp_member_count": ixps[0]["asn_count"] if ixps else None,
        },
        "carrier_diversity": {
            "peeringdb_carrier_count": len(carriers),
        }
    }

    for subsection_name, peeringdb_metrics in subsection_enhancements.items():
        if subsection_name in response_data and isinstance(response_data[subsection_name], dict):
            subsection = response_data[subsection_name]
            if "metrics" not in subsection:
                subsection["metrics"] = {
                    "numerical_values": {},
                    "percentages": {},
                    "ranges": {},
                    "units": {}
                }

            # Add PeeringDB metrics
            metrics = subsection["metrics"]
            for metric_key, metric_value in peeringdb_metrics.items():
                if metric_value is not None:
                    metrics["numerical_values"][metric_key] = metric_value
                    # Add unit
                    if "distance_km" in metric_key:
                        metrics["units"][metric_key] = "km"
                    elif "count" in metric_key:
                        metrics["units"][metric_key] = "count"

    # 5. Add structured tables for facilities, IXPs, carriers
    # Facilities table
    if facilities:
        facilities_table = {
            "title": "PeeringDB Colocation Facilities (Within 200km)",
            "headers": ["Facility Name", "Operator", "City/Country", "Distance (km)", "Data Quality", "Last Updated"],
            "rows": []
        }
        for fac in facilities[:10]:  # Top 10 closest
            data_quality = ", ".join(fac.get("data_quality_flag", [])) if fac.get("data_quality_flag") else "✓ Verified"
            facilities_table["rows"].append([
                fac.get("name", "Unknown"),
                fac.get("operator", "Unknown"),
                f"{fac.get('city', 'Unknown')}, {fac.get('country', 'Unknown')}",
                f"{fac.get('distance_km', 0):.1f}",
                data_quality,
                formatted_date
            ])

        # Inject facilities table into fiber_infrastructure subsection
        if "fiber_infrastructure" in response_data and isinstance(response_data["fiber_infrastructure"], dict):
            if "tables" not in response_data["fiber_infrastructure"]:
                response_data["fiber_infrastructure"]["tables"] = []
            response_data["fiber_infrastructure"]["tables"].append(facilities_table)

    # IXPs table
    if ixps:
        ixps_table = {
            "title": "PeeringDB Internet Exchange Points (Within 500km)",
            "headers": ["IXP Name", "City/Country", "ASN Count", "Type", "Distance (km)", "Data Quality", "Last Updated"],
            "rows": []
        }
        for ixp in ixps[:10]:
            data_quality = ", ".join(ixp.get("data_quality_flag", [])) if ixp.get("data_quality_flag") else "✓ Verified"
            ixp_type_display = ixp.get("ixp_type", "domestic").replace("_", " ").title()
            ixps_table["rows"].append([
                ixp.get("name", "Unknown"),
                f"{ixp.get('city', 'Unknown')}, {ixp.get('country', 'Unknown')}",
                str(ixp.get("asn_count", "N/A")),
                ixp_type_display,
                f"{ixp.get('distance_km', 0):.1f}",
                data_quality,
                formatted_date
            ])

        # Inject IXPs table into ixp_peering subsection
        if "ixp_peering" in response_data and isinstance(response_data["ixp_peering"], dict):
            if "tables" not in response_data["ixp_peering"]:
                response_data["ixp_peering"]["tables"] = []
            response_data["ixp_peering"]["tables"].append(ixps_table)

    # Carriers table
    if carriers:
        carriers_table = {
            "title": "PeeringDB Network Carriers (Present in Nearby Facilities)",
            "headers": ["Carrier Name"],
            "rows": [[carrier] for carrier in sorted(carriers)[:30]]  # Top 30
        }

        # Inject carriers table into carrier_diversity subsection
        if "carrier_diversity" in response_data and isinstance(response_data["carrier_diversity"], dict):
            if "tables" not in response_data["carrier_diversity"]:
                response_data["carrier_diversity"]["tables"] = []
            response_data["carrier_diversity"]["tables"].append(carriers_table)

    # 6. Update verification_metadata to include source names with dates (match OSM format)
    peeringdb_date = formatted_date if formatted_date != "Unknown" else last_updated
    if peeringdb_date == "Unknown":
        peeringdb_source_name = "PeeringDB"
    else:
        # Use parentheses format to match OSM: "PeeringDB (2024-12-08)"
        date_str = peeringdb_date[:10] if len(peeringdb_date) > 10 else peeringdb_date
        peeringdb_source_name = f"PeeringDB ({date_str})"

    subsection_verifications = {
        "fiber_infrastructure": ["peeringdb_facilities_within_200km"],
        "ixp_peering": ["peeringdb_ixps_within_500km", "peeringdb_nearest_ixp_distance_km", "peeringdb_nearest_ixp_member_count"],
        "carrier_diversity": ["peeringdb_carrier_count"]
    }

    for subsection_name, metric_keys in subsection_verifications.items():
        if subsection_name in response_data and isinstance(response_data[subsection_name], dict):
            subsection = response_data[subsection_name]
            if "verification_metadata" not in subsection:
                subsection["verification_metadata"] = {}

            for metric_key in metric_keys:
                # Special case: distance metrics with routing buffer are model inference (Fix 4)
                if "distance" in metric_key:
                    has_routing_buffer = any(
                        m.get("routing_buffer") is not None
                        for m in response_data.get("distance_measurements", [])
                    )
                    if has_routing_buffer:
                        subsection["verification_metadata"][metric_key] = {
                            "level": "model_inference",
                            "source": "PeeringDB coordinates + routing heuristic (aerial + 30%)"
                        }
                        continue

                # Default: verified by PeeringDB
                subsection["verification_metadata"][metric_key] = {
                    "level": "verified_by_peeringdb",
                    "source": peeringdb_source_name
                }

    return response_data


def detect_peeringdb_llm_conflicts(response_data: dict, peeringdb_data: dict) -> dict:
    """Detect conflicts between PeeringDB ground truth and LLM findings, generate CautionFlags"""
    if not peeringdb_data:
        return response_data

    if "caution_flags" not in response_data:
        response_data["caution_flags"] = []

    facilities = peeringdb_data.get("facilities", [])
    ixps = peeringdb_data.get("ixps", [])
    carriers = peeringdb_data.get("carriers", [])

    # CONFLICT 1: No facilities found in PeeringDB
    if not facilities:
        response_data["caution_flags"].append({
            "category": "infrastructure_availability",
            "severity": "high",
            "description": "PeeringDB found NO colocation facilities within 200 km search radius",
            "mitigation_plan": "Verify with regional fiber providers if facilities exist but are unmapped in PeeringDB. May require custom colocation build or long fiber runs to nearest facility.",
            "cost_impact": "Potentially +$2-10M for extended fiber infrastructure or custom colocation build if no nearby facilities confirmed",
            "timeline_impact": "+6-18 months for fiber construction and facility build-out",
            "severity_points": 0.8
        })

    # CONFLICT 2: No IXPs found in PeeringDB
    if not ixps:
        response_data["caution_flags"].append({
            "category": "infrastructure_availability",
            "severity": "medium",
            "description": "PeeringDB found NO Internet Exchange Points within 500 km search radius",
            "mitigation_plan": "Direct carrier peering may be required. Explore private peering options or remote IX port via dark fiber.",
            "cost_impact": "Higher transit costs without IX peering access (+$1-3M/year in transit costs)",
            "timeline_impact": "+3-6 months for private peering negotiations",
            "severity_points": 0.5
        })

    # CONFLICT 3: Limited carrier diversity
    if len(carriers) < 3 and facilities:
        response_data["caution_flags"].append({
            "category": "carrier_diversity",
            "severity": "medium",
            "description": f"PeeringDB shows only {len(carriers)} carriers in nearby facilities (minimum 3 recommended for redundancy)",
            "mitigation_plan": "Verify carrier availability directly with colocation facilities. May need to pre-qualify carrier diversity before site selection.",
            "cost_impact": "Limited carrier options may increase costs (+10-20% for transit/cross-connects)",
            "timeline_impact": "+2-4 months for carrier on-boarding if new builds required",
            "severity_points": 0.3
        })

    # CONFLICT 4: Data quality flags from PeeringDB
    quality_flagged_facilities = [f for f in facilities if f.get("data_quality_flag")]
    if quality_flagged_facilities:
        flag_summary = {}
        for fac in quality_flagged_facilities:
            for flag in fac.get("data_quality_flag", []):
                flag_summary[flag] = flag_summary.get(flag, 0) + 1

        response_data["caution_flags"].append({
            "category": "data_quality",
            "severity": "low",
            "description": f"PeeringDB data quality issues detected: {dict(flag_summary)}. This may indicate suspect coordinates, distributed locations, or missing operator data.",
            "mitigation_plan": "Verify facility coordinates and operator details directly with facility providers. Use city-level fallback distances where coordinates are suspect.",
            "cost_impact": "No direct cost impact, but affects distance/latency planning accuracy",
            "timeline_impact": None,
            "severity_points": 0.1
        })

    # CONFLICT 5: Distance discrepancy (compare PeeringDB vs LLM metrics)
    if facilities and "fiber_infrastructure" in response_data:
        fiber = response_data.get("fiber_infrastructure", {})
        if isinstance(fiber, dict) and "metrics" in fiber:
            metrics = fiber["metrics"]
            numerical = metrics.get("numerical_values", {})

            peeringdb_nearest_dist = facilities[0]["distance_km"]

            # Look for LLM-estimated facility distance
            llm_dist_keys = ["nearest_facility_km", "facility_distance_km", "colocation_distance_km"]
            for key in llm_dist_keys:
                if key in numerical:
                    llm_dist = numerical[key]
                    if isinstance(llm_dist, (int, float)):
                        diff = abs(llm_dist - peeringdb_nearest_dist)
                        pct_diff = (diff / peeringdb_nearest_dist) * 100 if peeringdb_nearest_dist > 0 else 0

                        if diff > 10 and pct_diff > 50:  # >10km AND >50% difference
                            response_data["caution_flags"].append({
                                "category": "data_quality",
                                "severity": "medium",
                                "description": f"Facility distance discrepancy: LLM estimate {llm_dist} km vs PeeringDB ground truth {peeringdb_nearest_dist} km (difference: {diff:.1f} km)",
                                "mitigation_plan": f"Use PeeringDB distance ({peeringdb_nearest_dist} km) as more reliable. Verify with fiber route survey.",
                                "cost_impact": "Distance affects fiber build costs (~$50K-150K per km)",
                                "timeline_impact": None,
                                "severity_points": 0.2
                            })
                            break

    # CONFLICT 6: IXP distance discrepancy
    if ixps and "ixp_peering" in response_data:
        ixp_section = response_data.get("ixp_peering", {})
        if isinstance(ixp_section, dict) and "metrics" in ixp_section:
            metrics = ixp_section["metrics"]
            numerical = metrics.get("numerical_values", {})

            peeringdb_nearest_ixp_dist = ixps[0]["distance_km"]

            # Look for LLM-estimated IXP distance
            llm_ixp_dist_keys = ["nearest_ixp_km", "ixp_distance_km", "exchange_distance_km"]
            for key in llm_ixp_dist_keys:
                if key in numerical:
                    llm_ixp_dist = numerical[key]
                    if isinstance(llm_ixp_dist, (int, float)):
                        diff = abs(llm_ixp_dist - peeringdb_nearest_ixp_dist)
                        pct_diff = (diff / peeringdb_nearest_ixp_dist) * 100 if peeringdb_nearest_ixp_dist > 0 else 0

                        if diff > 20 and pct_diff > 50:  # >20km AND >50% difference
                            response_data["caution_flags"].append({
                                "category": "data_quality",
                                "severity": "low",
                                "description": f"IXP distance discrepancy: LLM estimate {llm_ixp_dist} km vs PeeringDB {peeringdb_nearest_ixp_dist} km (difference: {diff:.1f} km)",
                                "mitigation_plan": f"Use PeeringDB distance ({peeringdb_nearest_ixp_dist} km) as baseline. Consider remote IX ports if local presence not available.",
                                "cost_impact": "Remote IX ports may require additional fiber costs",
                                "timeline_impact": None,
                                "severity_points": 0.1
                            })
                            break

    # CONFLICT 7: Old PeeringDB data warning
    last_updated = peeringdb_data.get("last_updated", "Unknown")
    if last_updated != "Unknown":
        try:
            from datetime import datetime
            # PeeringDB returns ISO timestamps like "2024-01-15T10:30:00Z"
            if "T" in last_updated:
                update_date = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            else:
                update_date = datetime.strptime(last_updated, "%Y-%m-%d")

            age_years = (datetime.now() - update_date.replace(tzinfo=None)).days / 365.25

            if age_years > 1:  # PeeringDB data >1 year old is concerning
                if "assumptions" not in response_data:
                    response_data["assumptions"] = []
                response_data["assumptions"].append(
                    f"PeeringDB data last updated {last_updated[:10]} ({age_years:.1f} years ago) - may not reflect recent facility additions or carrier expansions"
                )
        except Exception:
            pass

    return response_data


# --------------------------------------------------------------------------------
# Old-Style Agent Wrappers - Match Original Pattern Exactly
# --------------------------------------------------------------------------------

class PowerInfrastructureAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Power Infrastructure Agent"
        self.model = os.getenv('GEMINI_MODEL')
    async def analyze_power_infrastructure(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            # Extract location name from context if available
            location_name = None
            if context and isinstance(context, dict):
                location_name = context.get('location')

            # Step 1: Query OpenInfraMap for ground truth power infrastructure
            osm_data = None
            osm_error = None
            try:
                from agent.apis.power.power_infra_query import find_power_assets
                import json
                print(f"🔌 Querying OpenInfraMap for power infrastructure at {lat}, {lng}...")
                osm_data = find_power_assets(lat, lng)
                print(f"✅ OSM Query: Found {osm_data.get('nearest_substation_name', 'N/A')}")
                print(f"📊 OSM API Full Response:")
                print(json.dumps(osm_data, indent=2, ensure_ascii=False))
            except Exception as e:
                osm_error = str(e)
                print(f"⚠️ OSM Query Failed: {e}")
                # Continue without OSM data - not critical failure

            # Build location descriptor with location name if available
            if location_name:
                location_descriptor = f"{location_name} (coordinates: {lat}, {lng})"
                location_context_note = f'\n\n**LOCATION CONTEXT:** When referencing this site in summaries and key insights, use "{location_name}" as the canonical location name for consistency.'
            else:
                location_descriptor = f"coordinates {lat}, {lng}"
                location_context_note = ""

            # Use the ADK agent's instruction as the prompt base (like old code)
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze power infrastructure for data center at {location_descriptor} in {country}.{location_context_note}\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for electricity costs, grid capacity, utility information, renewable energy availability, and infrastructure data for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."

            # Inject OSM ground truth data
            if osm_data:
                osm_context = format_osm_for_prompt(osm_data)
                prompt = prompt + "\n\n" + osm_context
            elif osm_error:
                prompt = prompt + f"\n\n⚠️ Note: OpenInfraMap query failed ({osm_error}). Proceed with web search only."

            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled + schema enforcement")

            # Import the Pydantic model to enforce schema
            from .domain_models import PowerInfrastructureOutput

            # Call with grounding AND schema enforcement
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into PowerInfrastructureOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Validate response_data is a dict, not a list
                if not isinstance(response_data, dict):
                    raise ValueError(f"Power agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

                # Unwrap if LLM wrapped response in extra "power_infrastructure_output" key
                if "power_infrastructure_output" in response_data and len(response_data) == 1:
                    print(f"🔧 Unwrapping power_infrastructure_output wrapper")
                    response_data = response_data["power_infrastructure_output"]

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ Power Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Post-process: Enrich with OSM data and detect conflicts
                if osm_data:
                    response_data = enrich_power_output_with_osm(response_data, osm_data)
                    response_data = detect_osm_llm_conflicts(response_data, osm_data)

                # Try to create PowerInfrastructureOutput first (new format)
                try:
                    result = PowerInfrastructureOutput(**response_data)
                    return result
                except Exception as pydantic_error:
                    print(f"⚠️ PowerInfrastructureOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Power Agent JSON parsing failed: {json_error}")
                print(f"🔍 Cleaned response: {cleaned_response[:200]}...")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Power Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Power analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Power agent failed: {e}")
            # Return AgentOutput fallback for backward compatibility
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Power analysis failed: {str(e)}"],
                executive_summary="Power analysis unavailable"
            )

class NetworkConnectivityAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Network Connectivity Agent"
        self.model = os.getenv('GEMINI_MODEL')
    async def analyze_network_connectivity(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            # Import model locally (match power agent pattern)
            from .domain_models import NetworkConnectivityOutput

            # Note: context parameter kept for compatibility but not used

            # Step 1: Query PeeringDB for ground truth network infrastructure
            peeringdb_data = None
            peeringdb_error = None
            try:
                from agent.apis.network.network_query import query_peeringdb
                import json
                print(f"🌐 Querying PeeringDB for network infrastructure at {lat}, {lng}...")
                peeringdb_data = query_peeringdb(lat, lng, verbose=True)
                print(f"✅ PeeringDB Query: Found {len(peeringdb_data.get('facilities', []))} facilities, {len(peeringdb_data.get('ixps', []))} IXPs, {len(peeringdb_data.get('carriers', []))} carriers")
                print(f"📊 PeeringDB API Full Response:")
                print(json.dumps(peeringdb_data, indent=2, ensure_ascii=False))
            except Exception as e:
                peeringdb_error = str(e)
                print(f"⚠️ PeeringDB Query Failed: {e}")
                # Continue without PeeringDB data - not critical failure

            # Step 2: Build prompt with PeeringDB context
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze network connectivity for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for fiber infrastructure, internet exchange points, carrier presence, latency data, and network connectivity information for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."

            # Inject PeeringDB ground truth data
            if peeringdb_data:
                peeringdb_context = format_peeringdb_for_prompt(peeringdb_data)
                prompt = prompt + "\n\n" + peeringdb_context
            elif peeringdb_error:
                prompt = prompt + f"\n\n⚠️ Note: PeeringDB query failed ({peeringdb_error}). Proceed with web search only."

            # Step 3: Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled (NO schema enforcement - too restrictive)")

            # Call with grounding WITHOUT schema enforcement (let prompt guide output)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into NetworkConnectivityOutput

            # Debug: Check response status
            print(f"🔍 Network Agent Response Status: text={'present' if response.text else 'NONE'}, candidates={len(response.candidates) if hasattr(response, 'candidates') else 'N/A'}")
            if hasattr(response, 'prompt_feedback'):
                print(f"🔍 Prompt Feedback: {response.prompt_feedback}")

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Extract text from response - handle both .text and candidates[0] formats
                response_text = None
                if response.text:
                    response_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    # Try to extract from candidates[0].content
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content'):
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            response_text = candidate.content.parts[0].text
                        elif hasattr(candidate.content, 'text'):
                            response_text = candidate.content.text

                if not response_text:
                    error_msg = "Network agent returned empty response (no text in response.text or candidates)"
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                        error_msg += f" - Prompt feedback: {response.prompt_feedback}"
                    raise ValueError(error_msg)

                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response_text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Validate response_data is a dict, not a list
                if not isinstance(response_data, dict):
                    raise ValueError(f"Network agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

                # Unwrap if LLM wrapped response in extra "network_connectivity_output" key
                if "network_connectivity_output" in response_data and len(response_data) == 1:
                    print(f"🔧 Unwrapping network_connectivity_output wrapper")
                    response_data = response_data["network_connectivity_output"]

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ Network Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Post-process: Enrich with PeeringDB data
                if peeringdb_data:
                    response_data = enrich_network_output_with_peeringdb(response_data, peeringdb_data)

                # Detect conflicts between PeeringDB and LLM
                if peeringdb_data:
                    response_data = detect_peeringdb_llm_conflicts(response_data, peeringdb_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Network Agent: Injected {len(grounding_sources)} grounding sources + {len(existing_sources if isinstance(existing_sources, list) else [])} agent sources = {len(response_data['sources'])} total")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))
                        print(f"✅ Network Agent: Using {len(response_data['sources'])} agent-provided sources (no grounding sources)")
                    else:
                        print(f"⚠️ WARNING: Network Agent has NO sources - neither grounding nor agent-provided")
                        response_data["sources"] = []

                # Try to create NetworkConnectivityOutput first (new format)
                try:
                    network_output = NetworkConnectivityOutput(**response_data)

                    # Validate that subsections are populated if overall_score > 1.0
                    if network_output.overall_score > 1.0:
                        subsection_fields = [
                            'fiber_infrastructure', 'last_mile_diversity', 'subsea_cables',
                            'ixp_peering', 'carrier_diversity', 'latency_performance',
                            'bandwidth_costs', 'future_proofing'
                        ]
                        null_subsections = [
                            field for field in subsection_fields
                            if getattr(network_output, field, None) is None
                        ]

                        if len(null_subsections) == len(subsection_fields):
                            print(f"⚠️ WARNING: Network agent returned score {network_output.overall_score} but ALL subsections are NULL")
                            print(f"   This indicates incomplete LLM response. Sources present: {len(network_output.sources)}")
                        elif len(null_subsections) > 0:
                            print(f"⚠️ WARNING: {len(null_subsections)}/{len(subsection_fields)} network subsections are NULL: {null_subsections[:3]}")

                    return network_output
                except Exception as pydantic_error:
                    print(f"⚠️ NetworkConnectivityOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Network Agent JSON parsing failed: {json_error}")
                print(f"🔍 Cleaned response: {cleaned_response[:200]}...")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Network Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Network analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Network agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Network analysis failed: {str(e)}"],
                executive_summary="Network analysis unavailable"
            )

class ClimateSuitabilityAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Climate Suitability Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_climate_suitability(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze climate suitability for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for temperature data, humidity levels, natural disaster risks, cooling requirements, water availability, and climate information for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled + schema enforcement")

            # Import the Pydantic model to enforce schema
            from .domain_models import ClimateAnalysisOutput

            # Call with grounding AND schema enforcement
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into ClimateAnalysisOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Validate response_data is a dict, not a list
                if not isinstance(response_data, dict):
                    raise ValueError(f"Climate agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

                # Unwrap if LLM wrapped response in extra output key
                if "climate_hazards_output" in response_data and len(response_data) == 1:
                    print(f"🔧 Unwrapping climate_hazards_output wrapper")
                    response_data = response_data["climate_hazards_output"]

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ Climate Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create ClimateAnalysisOutput first (new format)
                try:
                    return ClimateAnalysisOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ ClimateAnalysisOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Climate Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Climate Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Climate analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Climate agent failed: {e}")
            # Return AgentOutput fallback for backward compatibility
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Climate analysis failed: {str(e)}"],
                executive_summary="Climate analysis unavailable"
            )

class OperationalRiskAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Operational Risk Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_operational_risk(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze operational risk for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for seismic risk, flood risk, political stability, security incidents, infrastructure reliability, and operational risk data for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into OperationalRiskOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ Risk Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create OperationalRiskOutput first (new format)
                try:
                    return OperationalRiskOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ OperationalRiskOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Risk Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Risk Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Risk analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Risk agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Risk analysis failed: {str(e)}"],
                executive_summary="Risk analysis unavailable"
            )

class SustainabilityESGAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Sustainability ESG Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_sustainability_esg(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze sustainability ESG for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for renewable energy adoption, carbon emission policies, environmental regulations, community impact, labor practices, and ESG performance data for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into ESGSustainabilityOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ ESG Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create ESGSustainabilityOutput first (new format)
                try:
                    return ESGSustainabilityOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ ESGSustainabilityOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ ESG Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ ESG Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"ESG analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ ESG agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"ESG analysis failed: {str(e)}"],
                executive_summary="ESG analysis unavailable"
            )

class RegulatoryESGAgentWrapper:
    """MERGED Regulatory & ESG Agent Wrapper (14% composite weight per expert spec)"""
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Regulatory & ESG Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_regulatory_esg(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze regulatory compliance AND ESG sustainability for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for: 1) Data protection laws, data residency requirements, government incentives, SEZ/FTZ benefits, permitting timelines, zoning requirements; 2) Grid renewable energy %, carbon intensity (gCO2/kWh), PPA market, carbon pricing, net-zero targets, ESG reporting requirements for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled + schema enforcement")

            # Import the Pydantic model to enforce schema
            from .domain_models import RegulatoryESGOutput

            # Call with grounding AND schema enforcement
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into RegulatoryComplianceOutput

            # Debug: Check response status
            print(f"🔍 Regulatory & ESG Agent Response Status: text={'present' if response.text else 'NONE'}, candidates={len(response.candidates) if hasattr(response, 'candidates') else 'N/A'}")
            if hasattr(response, 'prompt_feedback'):
                print(f"🔍 Prompt Feedback: {response.prompt_feedback}")

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Check if response has text content
                if not response.text:
                    error_msg = "Regulatory & ESG agent returned empty response (response.text is None or empty)"
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                        error_msg += f" - Prompt feedback: {response.prompt_feedback}"
                    raise ValueError(error_msg)

                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Validate response_data is a dict, not a list
                if not isinstance(response_data, dict):
                    raise ValueError(f"Regulatory ESG agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

                # Unwrap if LLM wrapped response in extra output key
                if "regulatory_esg_output" in response_data and len(response_data) == 1:
                    print(f"🔧 Unwrapping regulatory_esg_output wrapper")
                    response_data = response_data["regulatory_esg_output"]

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ Regulatory Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create RegulatoryESGOutput first (MERGED format)
                try:
                    from .domain_models import RegulatoryESGOutput
                    return RegulatoryESGOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ RegulatoryESGOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Regulatory & ESG Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Regulatory & ESG Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Regulatory & ESG analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Regulatory & ESG agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Regulatory & ESG analysis failed: {str(e)}"],
                executive_summary="Regulatory & ESG analysis unavailable"
            )

class HyperscalerAttractivenessAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Hyperscaler Attractiveness Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_hyperscaler_attractiveness(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze hyperscaler attractiveness for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis. Search for hyperscaler presence, competitive landscape, cloud ecosystem, peering opportunities, labor market, and market intelligence for this specific location.**\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into HyperscalerAttractivenessOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                pass

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    print(f"🔍 First 300 chars of response: {cleaned_response[:300]}")
                    repaired_response = repair_json_response(cleaned_response)
                    print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                    response_data = json.loads(repaired_response)

                # Normalize response for Pydantic
                response_data = normalize_pydantic_response(response_data)
                print(f"✅ Hyperscaler Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Backfill source names for verification_metadata (convert string "verified_by_public_source" to dict with source name)
                response_data = backfill_source_names_in_verification_metadata(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create HyperscalerAttractivenessOutput first (new format)
                try:
                    from .domain_models import HyperscalerAttractivenessOutput
                    return HyperscalerAttractivenessOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ HyperscalerAttractivenessOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Hyperscaler Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Hyperscaler Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Hyperscaler analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Hyperscaler agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Hyperscaler analysis failed: {str(e)}"],
                executive_summary="Hyperscaler analysis unavailable"
            )


class SiteCivilAgentWrapper:
    """Wrapper for Site & Civil Infrastructure Agent (matches proven pattern)"""
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Site & Civil Infrastructure Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_site_civil(self, lat, lng, country, context=None):
        """Execute site & civil infrastructure analysis"""
        try:
            # Use the ADK agent's instruction as the prompt base
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze site and civil infrastructure for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis.**"

            from google.genai import Client, types
            from google.genai.types import Tool, GoogleSearch
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} executing analysis with schema enforcement...")

            # Import the Pydantic model to enforce schema
            from .domain_models import SiteCivilInfrastructureOutput

            # Call with grounding AND schema enforcement
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Extract grounding sources
            grounding_sources = extract_grounding_sources(response)

            # Parse JSON response
            import json

            # Check if response.text is None with detailed debugging
            if not response.text:
                # Log response details for debugging
                print(f"❌ EMPTY RESPONSE DEBUGGING:")
                print(f"   Response object type: {type(response)}")
                print(f"   Response.text: {response.text}")
                if hasattr(response, 'candidates'):
                    print(f"   Candidates count: {len(response.candidates) if response.candidates else 0}")
                    if response.candidates:
                        candidate = response.candidates[0]
                        print(f"   Finish reason: {getattr(candidate, 'finish_reason', 'Unknown')}")
                        if hasattr(candidate, 'safety_ratings'):
                            print(f"   Safety ratings: {candidate.safety_ratings}")
                if hasattr(response, 'prompt_feedback'):
                    print(f"   Prompt feedback: {response.prompt_feedback}")
                raise Exception(f"Empty response from model - Check safety filters or API errors. Finish reason: {getattr(response.candidates[0], 'finish_reason', 'Unknown') if hasattr(response, 'candidates') and response.candidates else 'No candidates'}")

            cleaned_response = clean_agent_response(response.text)

            # Try to parse JSON, with repair if needed
            try:
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError as first_error:
                print(f"⚠️ Initial JSON parse failed, attempting repair...")
                repaired_response = repair_json_response(cleaned_response)
                response_data = json.loads(repaired_response)

            # Validate response_data is a dict, not a list
            if not isinstance(response_data, dict):
                raise ValueError(f"Site & Civil agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

            # Unwrap if LLM wrapped response in extra output key
            if "site_civil_output" in response_data and len(response_data) == 1:
                print(f"🔧 Unwrapping site_civil_output wrapper")
                response_data = response_data["site_civil_output"]

            response_data = normalize_pydantic_response(response_data)
            response_data = sanitize_metrics_data(response_data)

            # Inject grounding sources
            if grounding_sources:
                existing_sources = response_data.get("sources", [])
                combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                response_data["sources"] = sanitize_sources(combined_sources)
            elif "sources" in response_data:
                response_data["sources"] = sanitize_sources(response_data.get("sources", []))

            from .domain_models import SiteCivilInfrastructureOutput
            return SiteCivilInfrastructureOutput(**response_data)

        except Exception as e:
            print(f"❌ Site & Civil agent failed: {e}")
            from .domain_models import SiteCivilInfrastructureOutput
            return SiteCivilInfrastructureOutput(
                overall_score=1.0,
                land_availability={},
                geotechnical_conditions={},
                water_wastewater={},
                transportation_access={},
                permitting_timeline={},
                no_go_gates=[],
                caution_flags=[],
                sources=[],
                provenance_badges=[],
                distance_measurements=[],
                key_insights=[f"Site & civil analysis failed: {str(e)}"],
                executive_summary="Site & civil analysis unavailable"
            )


class MechanicalThermalAgentWrapper:
    """Wrapper for Mechanical & Thermal Infrastructure Agent (matches proven pattern)"""
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Mechanical & Thermal Infrastructure Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_mechanical_thermal(self, lat, lng, country, context=None):
        """Execute mechanical & thermal infrastructure analysis"""
        try:
            # Use the ADK agent's instruction as the prompt base
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze mechanical and thermal systems for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis.**"

            from google.genai import Client, types
            from google.genai.types import Tool, GoogleSearch
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} executing analysis with schema enforcement...")

            # Import the Pydantic model to enforce schema
            from .domain_models import MechanicalThermalOutput

            # Call with grounding AND schema enforcement
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Extract grounding sources
            grounding_sources = extract_grounding_sources(response)

            # Parse JSON response
            import json

            # Check if response has text
            if not response.text:
                raise ValueError("Mechanical & Thermal agent returned empty response")

            cleaned_response = clean_agent_response(response.text)

            # Check if cleaned response starts with valid JSON dict marker
            if not cleaned_response.strip().startswith('{'):
                print(f"⚠️ WARNING: Mechanical agent response doesn't start with '{{'. First 500 chars: {cleaned_response[:500]}")

            # Try to parse JSON, with repair if needed
            try:
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError as first_error:
                print(f"⚠️ Initial JSON parse failed, attempting repair...")
                print(f"🔍 First 300 chars of cleaned response: {cleaned_response[:300]}")
                repaired_response = repair_json_response(cleaned_response)
                print(f"🔍 First 300 chars after repair: {repaired_response[:300]}")
                response_data = json.loads(repaired_response)

            # Validate response_data is a dict, not a list
            if not isinstance(response_data, dict):
                print(f"❌ ERROR: Mechanical agent returned {type(response_data).__name__}")
                print(f"🔍 Full cleaned response (first 1000 chars): {cleaned_response[:1000]}")
                raise ValueError(f"Mechanical & Thermal agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

            # Unwrap if LLM wrapped response in extra output key
            if "mechanical_thermal_output" in response_data and len(response_data) == 1:
                print(f"🔧 Unwrapping mechanical_thermal_output wrapper")
                response_data = response_data["mechanical_thermal_output"]

            response_data = normalize_pydantic_response(response_data)
            response_data = sanitize_metrics_data(response_data)

            # Inject grounding sources
            if grounding_sources:
                existing_sources = response_data.get("sources", [])
                combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                response_data["sources"] = sanitize_sources(combined_sources)
            elif "sources" in response_data:
                response_data["sources"] = sanitize_sources(response_data.get("sources", []))

            from .domain_models import MechanicalThermalOutput
            return MechanicalThermalOutput(**response_data)

        except Exception as e:
            print(f"❌ Mechanical & Thermal agent failed: {e}")
            from .domain_models import MechanicalThermalOutput
            return MechanicalThermalOutput(
                overall_score=1.0,
                cooling_strategy={},
                hvac_design={},
                thermal_resilience={},
                water_treatment={},
                mechanical_systems={},
                no_go_gates=[],
                caution_flags=[],
                sources=[],
                provenance_badges=[],
                distance_measurements=[],
                key_insights=[f"Mechanical & thermal analysis failed: {str(e)}"],
                executive_summary="Mechanical & thermal analysis unavailable"
            )


class MarketCompetitionAgentWrapper:
    """Wrapper for Market & Competition Agent (matches proven pattern)"""
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Market & Competition Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_market_competition(self, lat, lng, country, context=None):
        """Execute market depth & competition analysis"""
        try:
            # Use the ADK agent's instruction as the prompt base
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze market dynamics and competition for data center at {lat}, {lng} in {country}.\n\n**MANDATORY: You MUST use web search to find current, factual data for this analysis.**"

            from google.genai import Client, types
            from google.genai.types import Tool, GoogleSearch
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} executing analysis (NO schema enforcement - too restrictive)")

            # Call with grounding WITHOUT schema enforcement (let prompt guide output)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Extract grounding sources
            grounding_sources = extract_grounding_sources(response)

            # Parse JSON response
            import json
            cleaned_response = clean_agent_response(response.text)

            # Try to parse JSON, with repair if needed
            try:
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError as first_error:
                print(f"⚠️ Initial JSON parse failed, attempting repair...")
                repaired_response = repair_json_response(cleaned_response)
                response_data = json.loads(repaired_response)

            # Validate response_data is a dict, not a list
            if not isinstance(response_data, dict):
                raise ValueError(f"Market & Competition agent returned {type(response_data).__name__} instead of dict. Response: {str(response_data)[:200]}")

            # Unwrap if LLM wrapped response in extra output key
            if "market_competition_output" in response_data and len(response_data) == 1:
                print(f"🔧 Unwrapping market_competition_output wrapper")
                response_data = response_data["market_competition_output"]

            response_data = normalize_pydantic_response(response_data)
            response_data = sanitize_metrics_data(response_data)

            # Inject grounding sources
            if grounding_sources:
                existing_sources = response_data.get("sources", [])
                combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                response_data["sources"] = sanitize_sources(combined_sources)
            elif "sources" in response_data:
                response_data["sources"] = sanitize_sources(response_data.get("sources", []))

            from .domain_models import MarketCompetitionOutput
            return MarketCompetitionOutput(**response_data)

        except Exception as e:
            print(f"❌ Market & Competition agent failed: {e}")
            from .domain_models import MarketCompetitionOutput
            return MarketCompetitionOutput(
                overall_score=1.0,
                competitive_landscape={},
                cloud_ecosystem={},
                peering_opportunities={},
                proximity_to_demand={},
                labor_market={},
                gtm_feasibility={},
                strategic_positioning={},
                no_go_gates=[],
                caution_flags=[],
                sources=[],
                provenance_badges=[],
                distance_measurements=[],
                key_insights=[f"Market & competition analysis failed: {str(e)}"],
                executive_summary="Market analysis unavailable"
            )


# --------------------------------------------------------------------------------
# Custom Parallel Analysis Function
# Run all domain agents in parallel with deterministic output control
# --------------------------------------------------------------------------------
async def generate_datacenter_report(location_context: LocationContext) -> str:
    """Generate comprehensive data center site analysis report with executive insights.

    Executes parallel analysis across all domains (Power, Network, Climate, Risk, ESG, Regulatory),
    creates structured report with executive summary, and returns business-focused insights.
    """

    try:
        # Handle dict input from ADK framework (convert to LocationContext)
        if isinstance(location_context, dict):
            location_context = LocationContext(**location_context)

        print(f"🚀 Starting parallel analysis for {location_context.location}")

        # Import agents locally to avoid circular imports
        from .power_agent import power_agent
        from .network_agent import network_agent
        from .climate_agent import climate_agent
        from .regulatory_esg_agent import regulatory_esg_agent  # MERGED regulatory + ESG (14% weight)
        from .site_civil_agent import site_civil_agent
        from .mechanical_thermal_agent import mechanical_thermal_agent
        from .market_competition_agent import market_competition_agent

        # Step 1: Create wrapped agents matching expert spec (7 domain agents)
        agents = {
            "power": PowerInfrastructureAgentWrapper(power_agent),
            "network": NetworkConnectivityAgentWrapper(network_agent),
            "climate": ClimateSuitabilityAgentWrapper(climate_agent),
            "regulatory_esg": RegulatoryESGAgentWrapper(regulatory_esg_agent),  # MERGED regulatory + ESG (14% weight)
            "site_civil": SiteCivilAgentWrapper(site_civil_agent),
            "mechanical_thermal": MechanicalThermalAgentWrapper(mechanical_thermal_agent),
            "market_competition": MarketCompetitionAgentWrapper(market_competition_agent),
        }

        # Extract coordinates for old interface
        lat, lng, country = location_context.lat, location_context.lng, location_context.country

        # Build shared context for all agents
        shared_context = {
            'location': location_context.location,
            'analysis_scale': location_context.analysis_scale,
            'justification': location_context.justification,
            'site_notes': location_context.site_notes
        }

        # Step 2: Run all 7 domain agents in parallel per expert specification
        print(f"🚀 Starting parallel analysis with 7 domain agents (per expert spec) for {location_context.location}")

        # Step 2: Execute 7 domain agents in parallel (per expert spec)
        agent_tasks = {
            "power": call_agent_with_retry(agents["power"], "analyze_power_infrastructure", lat, lng, country, shared_context),
            "network": call_agent_with_retry(agents["network"], "analyze_network_connectivity", lat, lng, country, shared_context),
            "climate": call_agent_with_retry(agents["climate"], "analyze_climate_suitability", lat, lng, country, shared_context),
            "regulatory_esg": call_agent_with_retry(agents["regulatory_esg"], "analyze_regulatory_esg", lat, lng, country, shared_context),  # MERGED regulatory + ESG
            "site_civil": call_agent_with_retry(agents["site_civil"], "analyze_site_civil", lat, lng, country, shared_context),
            "mechanical_thermal": call_agent_with_retry(agents["mechanical_thermal"], "analyze_mechanical_thermal", lat, lng, country, shared_context),
            "market_competition": call_agent_with_retry(agents["market_competition"], "analyze_market_competition", lat, lng, country, shared_context)
        }

        results = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)
        agent_results = dict(zip(agent_tasks.keys(), results))

        # Process results - convert old format to AgentOutput for compatibility
        processed_results = {}
        for key, result in agent_results.items():
            result_key = f"{key}_result"  # Convert "power" to "power_result"
            try:
                if isinstance(result, Exception):
                    print(f"❌ {key} failed: {str(result)}")
                    processed_results[result_key] = AgentOutput(
                        score=1.0,
                        insights=[f"Analysis failed: {str(result)}"],
                        detailed_analysis=f"Agent execution failed: {str(result)}",
                        summary=f"Could not complete {key} analysis due to error."
                    )
                else:
                    # Convert old dict format to AgentOutput
                    if isinstance(result, dict):
                        processed_results[result_key] = AgentOutput(**result)
                    else:
                        processed_results[result_key] = result
                    print(f"✅ {result_key} completed - Score: {processed_results[result_key].overall_score}")
            except Exception as e:
                print(f"❌ Error processing {key} result: {str(e)}")
                processed_results[result_key] = AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Result processing failed: {str(e)}"],
                    executive_summary=f"Failed to process {key} analysis result."
                )

        agent_results = processed_results

        print(f"🔄 Parallel analysis completed. Generating intelligent insights...")

        # Step 2: Calculate weighted composite score with NO-GO gate checks (INVESTMENT-GRADE)
        composite_score, weighted_scores, all_no_go_gates, all_caution_flags = calculate_weighted_composite_score(agent_results)

        print(f"🎯 Investment-Grade Composite Score: {composite_score:.2f}/5.0")
        if all_no_go_gates:
            triggered = [g for g in all_no_go_gates if g.triggered]
            print(f"🚫 NO-GO Gates: {len(triggered)} triggered, {len(all_no_go_gates)-len(triggered)} passed")
        if all_caution_flags:
            print(f"⚠️  Caution Flags: {len(all_caution_flags)} requiring mitigation")

        # Step 3: Generate intelligent insights using cross-domain synthesis
        from .insights_agent import insights_agent, prepare_insights_input

        insights_input = prepare_insights_input(
            location_context=location_context,
            composite_score=composite_score,
            power_result=agent_results['power_result'],
            network_result=agent_results['network_result'],
            climate_result=agent_results['climate_result'],
            regulatory_esg_result=agent_results['regulatory_esg_result'],  # MERGED regulatory + ESG domain (14% weight)
            # Include remaining 3 domain agents
            site_civil_result=agent_results.get('site_civil_result'),
            mechanical_thermal_result=agent_results.get('mechanical_thermal_result'),
            market_competition_result=agent_results.get('market_competition_result')
        )

        print(f"🧠 Calling insights agent for intelligent synthesis...")
        try:
            # Call insights agent using direct Gemini API (like other wrappers)
            import google.generativeai as genai
            import os
            import json

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(insights_agent.model)

            # Create prompt with insights input data
            prompt = f"{insights_agent.instruction}\n\nAnalyze the following cross-domain data and provide intelligent insights:\n\n{json.dumps(insights_input.model_dump(), indent=2)}"

            print(f"📤 Sending prompt to insights agent (length: {len(prompt)} chars)")
            response = await asyncio.to_thread(model.generate_content, prompt)
            print(f"📥 Received response from insights agent (length: {len(response.text)} chars)")

            # Parse JSON response with robust error handling
            insights_data = robust_json_parse(response.text, "insights agent response")

            # Convert to InsightsOutput model
            from .models import InsightsOutput
            insights_result = InsightsOutput(**insights_data)
            print(f"✅ Insights agent completed successfully")

        except Exception as e:
            print(f"⚠️ Insights agent failed, using fallback: {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            # Log more details for debugging
            if hasattr(e, 'response'):
                print(f"📄 Response that failed: {e.response[:1000]}...")
            insights_result = None

        # Step 4: Create ReportSchema with intelligent insights and INVESTMENT-GRADE data
        report_schema = ReportSchema.from_location_and_agents(
            location_context=location_context,
            power_result=agent_results['power_result'],
            network_result=agent_results['network_result'],
            climate_result=agent_results['climate_result'],
            regulatory_esg_result=agent_results['regulatory_esg_result'],  # MERGED regulatory + ESG domain (14% weight)
            # Include remaining 3 domain agents per Expert Spec
            site_civil_result=agent_results.get('site_civil_result'),
            mechanical_thermal_result=agent_results.get('mechanical_thermal_result'),
            market_competition_result=agent_results.get('market_competition_result'),
            insights_result=insights_result,  # Pass intelligent insights
            # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
            weighted_domain_scores=weighted_scores,
            all_no_go_gates=all_no_go_gates,  # Pass raw model instances
            all_caution_flags=all_caution_flags,  # Pass raw model instances
            composite_score_override=composite_score  # Use weighted composite score
        )
        print(f"✅ ReportSchema created with intelligent insights - Overall Score: {report_schema.overall_suitability.composite_score}")

        # Step 3: Direct JSON generation
        json_result = save_report_schema(report_schema)
        print(f"✅ JSON saved: {json_result.get('file_path', 'Unknown')}")

        # Step 3.5: Auto-save to database
        try:
            db_result = save_report_to_database(report_schema)
            print(f"✅ Database: {db_result}")
        except Exception as e:
            print(f"⚠️ Database save failed: {e}")

        # Step 4: Generate executive summary response (INVESTMENT-GRADE ONE-PAGER FORMAT)
        def generate_executive_response(report: "ReportSchema") -> str:
            """Generate executive one-pager per Expert Specification"""
            try:
                # Round the score for display
                rounded_score = round(report.overall_suitability.composite_score, 2)

                # Create response with investment-grade format
                response = f"📊 **INVESTMENT-GRADE EXECUTIVE ONE-PAGER**\n\n"
                response += f"🏢 **Site**: {report.location}, {report.country}\n"
                response += f"📅 **Analysis Date**: {report.analysis_date}\n\n"

                # 1. Overall Suitability
                response += f"• **Overall Suitability**: {rounded_score} / 5.00 ({report.overall_suitability.rating})\n\n"

                # 1.5. Investment Verdict (based on score and NO-GO gates)
                if report.overall_suitability.no_go_triggered:
                    verdict = "❌ NO-GO"
                    verdict_detail = "Site fails critical investment gates - NOT RECOMMENDED for development"
                elif rounded_score >= 4.0:
                    verdict = "✅ INVEST"
                    verdict_detail = "Strong fundamentals across all domains - RECOMMENDED for investment"
                elif rounded_score >= 3.0:
                    verdict = "⚠️ PROCEED WITH CAUTION"
                    verdict_detail = "Viable with mitigations - Conditional PROCEED pending risk mitigation"
                else:
                    verdict = "⚠️ HIGH RISK"
                    verdict_detail = "Significant challenges identified - Requires comprehensive risk analysis"

                response += f"• **Investment Verdict**: {verdict}\n"
                response += f"    {verdict_detail}\n\n"

                # 2. Hard Gates (NO-GO gates)
                response += f"• **Hard Gates**: "
                if report.overall_suitability.no_go_triggered:
                    response += f"❌ FAILED - {len(report.overall_suitability.failed_gates)} gate(s) triggered\n"
                    for gate_name in report.overall_suitability.failed_gates[:3]:
                        response += f"    - {gate_name}\n"
                else:
                    response += f"✅ PASSED - All critical NO-GO gates cleared\n"
                response += "\n"

                # 3. Top Drivers (from strengths) - Show top 5, no padding with generic placeholders
                strengths = report.executive_summary.key_strengths[:5] if report.executive_summary.key_strengths else []
                response += f"• **Top Drivers** ({len(strengths)}):\n\n"
                for i, strength in enumerate(strengths, 1):
                    clean_strength = strength.split(':')[0] if ':' in strength else strength
                    response += f"  {i}. {clean_strength}\n"
                response += "\n"

                # 4. Key Risks (from challenges and caution flags) - Show top 5, no padding with generic placeholders
                challenges = report.executive_summary.key_challenges[:5] if report.executive_summary.key_challenges else []
                response += f"• **Key Risks** ({len(challenges)}):\n\n"
                for i, challenge in enumerate(challenges, 1):
                    clean_challenge = challenge.split(':')[0] if ':' in challenge else challenge
                    response += f"  {i}. {clean_challenge}\n"
                response += "\n"

                # 5. Mitigations (from phase 1 risk mitigation) - Show top 5, no padding with generic placeholders
                phase1 = report.phase_1_deployment
                mitigations = phase1.risk_mitigation[:5] if hasattr(phase1, 'risk_mitigation') and phase1.risk_mitigation else []
                response += f"• **Mitigations** ({len(mitigations)}):\n\n"
                for i, mitigation in enumerate(mitigations, 1):
                    response += f"  {i}. {mitigation}\n"
                response += "\n"

                # 6. Time-to-Power (extract from power domain or phase 1)
                response += f"• **Time-to-Power (est)**: 18-36 months; **Critical Path**: Grid interconnection, permitting, substation buildout\n\n"

                # 7. CapEx & OpEx Drivers
                response += f"• **CapEx Drivers**: {phase1.estimated_investment} - Power infrastructure, cooling systems, site development, IT equipment\n\n"
                response += f"• **OpEx Drivers**: Electricity costs (dominant), network bandwidth, labor, maintenance, property taxes\n\n"

                # 8. Next Proofs (Transactional)
                response += f"• **Next Proofs (Transactional)**:\n"
                all_third_party = []
                for agent_key, agent_result in agent_results.items():
                    if hasattr(agent_result, 'third_party_verification') and agent_result.third_party_verification:
                        all_third_party.extend(agent_result.third_party_verification)

                if all_third_party:
                    for verification in list(set(all_third_party))[:5]:
                        response += f"    - {verification}\n"
                else:
                    response += f"    - Utility interconnection letter of intent\n"
                    response += f"    - Carrier fiber route survey and LOI\n"
                    response += f"    - PPA/VPA renewable energy quote\n"
                    response += f"    - Phase I Environmental Site Assessment\n"
                    response += f"    - Title commitment and zoning verification\n"
                response += "\n"

                # 9. Confidence
                confidence_level = report.overall_suitability.confidence_level or "medium"
                verification_pct = report.overall_suitability.verification_percentage or 40.0
                response += f"• **Confidence**: {confidence_level.upper()} ({verification_pct:.0f}% verified data)\n"
                response += f"    Analysis based on {len(agent_results)} domain assessments with public data sources.\n"
                response += f"    {report.overall_suitability.caution_count} caution flags identified requiring mitigation.\n\n"

                # 10. Phase 1 Priorities (actionable next steps)
                response += f"• **Phase 1 Priorities** (Top 5 Actions):\n\n"
                phase1_priorities = phase1.priority_recommendations[:5] if hasattr(phase1, 'priority_recommendations') and phase1.priority_recommendations else []
                if phase1_priorities:
                    for i, priority in enumerate(phase1_priorities, 1):
                        response += f"  {i}. {priority}\n"
                else:
                    # Generate default priorities based on score and challenges
                    if rounded_score >= 4.0:
                        response += f"  1. Secure utility interconnection LOI and timeline commitment\n"
                        response += f"  2. Initiate fiber carrier outreach for diverse route confirmation\n"
                        response += f"  3. Commission Phase I Environmental Site Assessment\n"
                        response += f"  4. Engage land/title company for due diligence\n"
                        response += f"  5. Develop preliminary site plan and permitting strategy\n"
                    elif rounded_score >= 3.0:
                        response += f"  1. Address top 3 caution flags with mitigation cost analysis\n"
                        response += f"  2. Secure utility capacity confirmation and grid study\n"
                        response += f"  3. Verify fiber route diversity with carrier site visits\n"
                        response += f"  4. Conduct market feasibility study (CBRE/JLL)\n"
                        response += f"  5. Assess regulatory timeline and permitting complexity\n"
                    else:
                        response += f"  1. Resolve critical NO-GO gates or site vulnerabilities\n"
                        response += f"  2. Commission third-party infrastructure assessment\n"
                        response += f"  3. Evaluate alternative site locations in region\n"
                        response += f"  4. Perform detailed risk-cost-benefit analysis\n"
                        response += f"  5. Consider partnerships to share development risk\n"
                response += "\n"

                response += f"📋 **Full JSON report saved** | 🔍 {len(agent_results)} domains analyzed\n"

                return response

            except Exception as e:
                print(f"⚠️ Error generating executive response: {e}")
                return f"✅ Analysis complete for {report.location} - Overall Score: {rounded_score}/5.0 ({report.overall_suitability.rating})"

        final_message = generate_executive_response(report_schema)
        return final_message

    except Exception as e:
        import traceback
        error_message = (
            f"❌ Complete analysis pipeline failed: {str(e)}\n"
            f"🔍 Traceback: {traceback.format_exc()}"
        )
        print(error_message)
        return error_message

# Use the async function directly - FunctionTool should handle async functions
datacenter_report_tool = FunctionTool(func=generate_datacenter_report)

# All wrapper functions removed - logic moved into generate_datacenter_report


