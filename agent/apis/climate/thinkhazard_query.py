#!/usr/bin/env python3
"""
ThinkHazard Query Module (Global Multi-Hazard Screen)

Queries the World Bank ThinkHazard API for hazard levels at given coordinates.
Returns: Flood, Cyclone, Earthquake, Drought risk levels (Low/Medium/High)

Workflow:
1. Reverse geocode coordinates -> country ISO code
2. Search ThinkHazard for admin divisions in that country
3. Find closest admin division to coordinates
4. Query hazard report for that division

API: https://thinkhazard.org (GFDRR/World Bank)
Auth: None required (public API)
"""
import requests
import math
from typing import Dict, Any, Optional, List


THINKHAZARD_BASE = "https://thinkhazard.org"

# Hazard level mapping
HAZARD_LEVELS = {
    "HIG": "High",
    "MED": "Medium",
    "LOW": "Low",
    "VLO": "Very Low",
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, str]]:
    """
    Reverse geocode coordinates to get location details using Nominatim (OSM).
    Returns dict with country_code, country, state, and county (when available).
    For US locations, uses higher zoom to get county-level data.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    headers = {"User-Agent": "HazardQueryTool/1.0"}

    # First, get country to determine if US (need county level)
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,  # county level for detailed info
        "addressdetails": 1,
        "accept-language": "en",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address", {})
            return {
                "country_code": address.get("country_code", "").upper(),
                "country": address.get("country", ""),
                "state": address.get("state", ""),
                "county": address.get("county", ""),
            }
    except Exception:
        pass
    return None


def search_thinkhazard_divisions(query: str) -> List[Dict[str, Any]]:
    """
    Search ThinkHazard for admin divisions matching a query (country name).
    Returns list of divisions with code, admin0 (country name), url.
    """
    url = f"{THINKHAZARD_BASE}/en/administrativedivision"
    params = {"q": query}

    try:
        resp = requests.get(url, params=params, timeout=15,
                          headers={"Accept": "application/json"})
        if resp.status_code == 200:
            data = resp.json()
            # Response is wrapped in "data" key
            return data.get("data", []) if isinstance(data, dict) else data
    except Exception:
        pass
    return []


def get_hazard_report(division_code: int) -> Optional[List[Dict[str, Any]]]:
    """
    Get hazard report for a specific admin division code.
    Returns list of hazard categories with hazardtype and hazardlevel.
    """
    url = f"{THINKHAZARD_BASE}/en/report/{division_code}.json"

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # Response is a list of hazard categories directly
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return None


def find_country_division(country_name: str) -> Optional[Dict[str, Any]]:
    """Find the country-level division for a country name."""
    divisions = search_thinkhazard_divisions(country_name)

    # Response format: {"code": 259, "admin0": "United States of America", "url": "..."}
    # Return first matching result (should be country level)
    if divisions and isinstance(divisions, list) and len(divisions) > 0:
        return divisions[0]

    return None


def find_best_division(geo_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Find the most granular administrative division for the location.
    For US: Try county (ADM2) -> state (ADM1) -> country (ADM0)
    For non-US: Country level with granularity note.

    Returns dict with 'division', 'admin_level', and 'granularity_note'.
    """
    country_code = geo_info.get("country_code", "").upper()
    country = geo_info.get("country", "")
    state = geo_info.get("state", "")
    county = geo_info.get("county", "")

    result = {
        "division": None,
        "admin_level": None,
        "admin_name": None,
        "state": None,
        "granularity_note": None,
    }

    # For US locations, try to get county-level data
    if country_code == "US" and county and state:
        # Search for county + state combination
        # ThinkHazard format: "County Name, State Name" or just county name
        search_queries = [
            f"{county}, {state}",
            county,
            f"{county} County, {state}",
        ]

        for query in search_queries:
            divisions = search_thinkhazard_divisions(query)
            if divisions:
                # Look for ADM2 level matches (have admin2 field)
                for div in divisions:
                    if div.get("admin2"):
                        result["division"] = div
                        result["admin_level"] = "ADM2"
                        result["admin_name"] = div.get("admin2", county)
                        result["state"] = state
                        return result

        # Fallback to state level for US
        if state:
            divisions = search_thinkhazard_divisions(state)
            if divisions:
                for div in divisions:
                    # ADM1 has admin1 but no admin2
                    if div.get("admin1") and not div.get("admin2"):
                        result["division"] = div
                        result["admin_level"] = "ADM1"
                        result["admin_name"] = div.get("admin1", state)
                        result["state"] = state
                        result["granularity_note"] = "State-level data; county-level not available"
                        return result

    # Fallback to country level for non-US or when granular data unavailable
    division = find_country_division(country)
    if not division:
        # Try country code
        division = find_country_division(country_code)

    if division:
        result["division"] = division
        result["admin_level"] = "ADM0"
        result["admin_name"] = division.get("admin0", country)
        if country_code == "US":
            result["granularity_note"] = "Country-level data; finer granularity not available"
        else:
            result["granularity_note"] = "Country-level data used"

    return result


def query_thinkhazard(lat: float, lon: float) -> Dict[str, Any]:
    """
    Query ThinkHazard for multi-hazard risk levels at given coordinates.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Dictionary with hazard levels and metadata:
        - flood: str (Low/Medium/High/Very Low/No Data)
        - cyclone: str
        - earthquake: str
        - drought: str
        - admin_name: str (name of admin division used)
        - admin_level: str (ADM0/ADM1/ADM2)
        - dataset_vintage: str
        - data_confidence: str (high/medium/low)
    """
    result = {
        "flood": "No Data",
        "cyclone": "No Data",
        "earthquake": "No Data",
        "drought": "No Data",
        "admin_name": None,
        "admin_level": None,
        "state": None,
        "country": None,
        "division_code": None,
        "granularity_note": None,
        "dataset_vintage": "2017-2020 (ThinkHazard v2, underlying hazard data varies by type)",
        "data_source": "thinkhazard.org",
        "data_confidence": None,
    }

    # Step 1: Reverse geocode to get location details (country, state, county)
    geo = reverse_geocode(lat, lon)
    if not geo or not geo.get("country"):
        result["error"] = "Could not determine country from coordinates"
        return result

    result["country"] = geo["country"]

    # Step 2: Find best available admin division (ADM2 for US, ADM0 for others)
    division_info = find_best_division(geo)

    if not division_info.get("division"):
        result["error"] = f"Location '{geo['country']}' not found in ThinkHazard"
        return result

    division = division_info["division"]
    division_code = division.get("code")

    result["admin_name"] = division_info.get("admin_name")
    result["admin_level"] = division_info.get("admin_level")
    result["division_code"] = division_code

    if division_info.get("state"):
        result["state"] = division_info["state"]

    if division_info.get("granularity_note"):
        result["granularity_note"] = division_info["granularity_note"]

    # Step 3: Get hazard report for the division
    hazards = get_hazard_report(division_code)
    if hazards is None:
        result["error"] = f"Could not fetch hazard report for division {division_code}"
        return result

    # Step 4: Extract hazard levels
    # ThinkHazard uses: FL=River flood, UF=Urban flood, CF=Coastal flood,
    # EQ=Earthquake, CY=Cyclone, DG=Water scarcity (drought)
    for hazard in hazards:
        htype = hazard.get("hazardtype", {}).get("mnemonic", "")
        level = hazard.get("hazardlevel", {}).get("mnemonic", "")
        level_label = HAZARD_LEVELS.get(level, level if level else "No Data")

        if htype == "FL":  # River flood
            result["flood"] = level_label
        elif htype == "CY":  # Cyclone
            result["cyclone"] = level_label
        elif htype == "EQ":  # Earthquake
            result["earthquake"] = level_label
        elif htype == "DG":  # Water scarcity = drought proxy
            result["drought"] = level_label

    # Set data confidence based on admin level
    result["data_confidence"] = "high"  # ThinkHazard is authoritative source

    return result


def format_human_summary(res: Dict[str, Any]) -> str:
    """Format results as human-readable summary."""
    admin = res.get("admin_name") or res.get("country") or "Unknown"
    return (
        f"ThinkHazard Report for {admin}:\n"
        f"  Flood: {res.get('flood', 'No Data')}\n"
        f"  Cyclone: {res.get('cyclone', 'No Data')}\n"
        f"  Earthquake: {res.get('earthquake', 'No Data')}\n"
        f"  Drought: {res.get('drought', 'No Data')}"
    )


if __name__ == "__main__":
    import json

    test_coords = [
        (33.405528, -79.983507, "Russellville, SC"),
        (51.0530, 16.1921, "Jawor, Poland"),
        (26.3097274, 49.8100201, "Dammam, KSA"),
    ]

    for lat, lon, name in test_coords:
        print(f"\n{'='*60}")
        print(f"Querying ThinkHazard for {name} ({lat}, {lon})...")
        print("="*60)

        result = query_thinkhazard(lat, lon)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\nHuman summary:")
        print(format_human_summary(result))
