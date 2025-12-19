#!/usr/bin/env python3
"""
API Registry - Central documentation of API->Agent mappings and configurable thresholds.

This file serves as the single source of truth for:
1. Which APIs feed which agents
2. Configurable thresholds for cross-domain alerts
3. Verification tags for each API source
"""

# =============================================================================
# API -> AGENT MAPPINGS
# =============================================================================

API_AGENT_MAPPINGS = {
    # Infrastructure Registry APIs
    "peeringdb": {
        "file": "infrastructure_registry/network_query.py",
        "function": "query_peeringdb",
        "primary_agents": ["network"],
        "cross_domain_agents": ["market"],  # NOT ESG per client feedback
        "verification_tag": "verified_by_peeringdb",
        "data_provided": ["facilities", "ixps", "carriers", "distances"]
    },
    "osm_power": {
        "file": "infrastructure_registry/power_infra_query.py",
        "function": "find_power_assets",
        "primary_agents": ["power"],
        "cross_domain_agents": ["site_civil"],
        "verification_tag": "verified_by_osm",
        "data_provided": ["substations", "voltages", "transmission_lines", "distances"]
    },

    # Geospatial Hazard APIs
    "seismic": {
        "file": "geospatial_hazards/seismic_hazard_query.py",
        "function": "query_seismic_hazard",
        "primary_agents": ["climate"],
        "cross_domain_agents": ["power", "network", "site_civil", "mechanical"],
        "verification_tag": "verified_by_usgs",
        "data_provided": ["pga_g", "risk_label", "return_period"]
    },
    "flood": {
        "file": "geospatial_hazards/flood_hazard_query.py",
        "function": "query_flood_hazard",
        "primary_agents": ["climate"],
        "cross_domain_agents": [],  # Climate-only
        "verification_tag": "verified_by_glofas",
        "data_provided": ["flood_risk_category", "return_period"]
    },
    "protected_areas": {
        "file": "geospatial_hazards/protected_area_query.py",
        "function": "query_protected_area",
        "primary_agents": ["climate"],
        "cross_domain_agents": ["network", "regulatory_esg"],
        "verification_tag": "verified_by_wdpa",
        "data_provided": ["inside_protected_area", "distance_km", "iucn_category"]
    },
    "thinkhazard": {
        "file": "geospatial_hazards/thinkhazard_query.py",
        "function": "query_thinkhazard",
        "primary_agents": ["climate"],
        "cross_domain_agents": [],  # Climate-only
        "verification_tag": "verified_by_worldbank",
        "data_provided": ["flood", "earthquake", "cyclone", "wildfire"]
    },

    # Resource Stress APIs
    "water_stress": {
        "file": "resource_stress/water_stress_query.py",
        "function": "query_water_stress",
        "primary_agents": ["site_civil"],
        "cross_domain_agents": ["power", "mechanical", "regulatory_esg", "market"],
        "verification_tag": "verified_by_wri_aqueduct",
        "data_provided": ["baseline_water_stress_score", "category"]
    },

    # Routing APIs (FUTURE)
    "osrm": {
        "file": "routing/osrm_query.py",
        "function": "query_road_distance",
        "primary_agents": [],
        "cross_domain_agents": ["site_civil", "network"],
        "verification_tag": "verified_by_osrm",
        "data_provided": ["road_distance_km", "duration_minutes"],
        "status": "planned"
    },
}


# =============================================================================
# CONFIGURABLE THRESHOLDS
# =============================================================================

CROSS_DOMAIN_THRESHOLDS = {
    # Water Stress thresholds
    "water_stress_high": 3.0,          # Score >3 = HIGH stress, evaporative cooling limited
    "water_stress_extreme": 4.0,       # Score >4 = EXTREME stress, water-cooled NOT recommended

    # Seismic thresholds
    "seismic_pga_moderate": 0.1,       # PGA >0.1g = equipment seismic bracing required
    "seismic_pga_high": 0.3,           # PGA >0.3g = significant structural hardening
    "seismic_pga_very_high": 0.5,      # PGA >0.5g = special seismic design required

    # Protected Area thresholds
    "protected_area_buffer_km": 5.0,   # Distance <5km = route/placement restrictions apply
    "protected_area_critical_km": 1.0, # Distance <1km = potential NO-GO

    # Carrier diversity thresholds
    "carrier_minimum": 3,              # <3 carriers = vendor concentration risk
    "ixp_minimum": 2,                  # <2 IXPs = limited peering options
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_agents_for_api(api_name: str) -> list:
    """Get all agents that consume a given API."""
    api = API_AGENT_MAPPINGS.get(api_name, {})
    return api.get("primary_agents", []) + api.get("cross_domain_agents", [])


def get_apis_for_agent(agent_name: str) -> list:
    """Get all APIs that feed a given agent."""
    apis = []
    for api_name, api_info in API_AGENT_MAPPINGS.items():
        if agent_name in api_info.get("primary_agents", []) + api_info.get("cross_domain_agents", []):
            apis.append(api_name)
    return apis


def get_threshold(threshold_name: str, default=None):
    """Get a configurable threshold value."""
    return CROSS_DOMAIN_THRESHOLDS.get(threshold_name, default)


def check_water_stress_alert(score: float) -> str:
    """Check water stress level and return alert status."""
    if score is None:
        return "UNKNOWN"
    if score > get_threshold("water_stress_extreme"):
        return "EXTREME - water-cooled cooling NOT recommended"
    elif score > get_threshold("water_stress_high"):
        return "HIGH - evaporative cooling limited"
    return "ACCEPTABLE"


def check_seismic_alert(pga_g: float) -> str:
    """Check seismic PGA and return alert status."""
    if pga_g is None:
        return "UNKNOWN"
    if pga_g > get_threshold("seismic_pga_very_high"):
        return "VERY HIGH - special seismic design required"
    elif pga_g > get_threshold("seismic_pga_high"):
        return "HIGH - significant structural hardening"
    elif pga_g > get_threshold("seismic_pga_moderate"):
        return "MODERATE - equipment seismic bracing required"
    return "LOW - standard foundations acceptable"


def check_protected_area_alert(distance_km: float, inside: bool) -> str:
    """Check protected area proximity and return alert status."""
    if inside:
        return "INSIDE - potential NO-GO zone"
    if distance_km is None:
        return "UNKNOWN"
    if distance_km < get_threshold("protected_area_critical_km"):
        return "CRITICAL - <1km from protected area"
    if distance_km < get_threshold("protected_area_buffer_km"):
        return "CAUTION - route/placement restrictions may apply"
    return "CLEAR - no restrictions"


def get_verification_tag(api_name: str) -> str:
    """Get the verification tag for an API."""
    api = API_AGENT_MAPPINGS.get(api_name, {})
    return api.get("verification_tag", f"verified_by_{api_name}")
