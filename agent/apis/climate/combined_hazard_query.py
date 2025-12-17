#!/usr/bin/env python3
"""
Combined Climate Hazard Query Module

Fetches ALL climate/hazard API data in PARALLEL for optimal performance.
This runs BEFORE the Gemini API call so agents have complete ground-truth
data as context for analysis and scoring.

APIs Fetched:
- Seismic Hazard (USGS/GEM)
- Flood Hazard (GloFAS v4)
- Protected Areas (WDPA via GEE)
- ThinkHazard (World Bank multi-hazard)

Auth: GEE Service Account required for protected_areas
"""
import asyncio
from typing import Dict, Any
from datetime import datetime


async def query_all_climate_hazards(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetch ALL climate/hazard API data in PARALLEL.

    This runs BEFORE the Gemini API call so agents have complete
    ground-truth data as context for analysis and scoring.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Dict with keys: seismic_hazard, flood_hazard, protected_areas,
        thinkhazard, query_timestamp, errors
    """
    from .seismic_hazard_query import query_seismic_hazard
    from .flood_hazard_query import query_flood_hazard
    from agent.apis.climate_site_civil_regulatory_esg.protected_area_query import query_protected_area
    from .thinkhazard_query import query_thinkhazard

    results = {
        "query_timestamp": datetime.utcnow().isoformat(),
        "coordinates": {"lat": lat, "lon": lon},
        "seismic_hazard": None,
        "flood_hazard": None,
        "protected_areas": None,
        "thinkhazard": None,
        "errors": {}
    }

    # Async wrappers for sync functions
    async def fetch_seismic():
        try:
            return await asyncio.to_thread(query_seismic_hazard, lat, lon)
        except Exception as e:
            return {"error": str(e)}

    async def fetch_flood():
        try:
            return await asyncio.to_thread(query_flood_hazard, lat, lon)
        except Exception as e:
            return {"error": str(e)}

    async def fetch_protected():
        try:
            return await asyncio.to_thread(query_protected_area, lat, lon)
        except Exception as e:
            return {"error": str(e)}

    async def fetch_thinkhazard():
        try:
            return await asyncio.to_thread(query_thinkhazard, lat, lon)
        except Exception as e:
            return {"error": str(e)}

    # Execute ALL queries in PARALLEL
    seismic, flood, protected, think = await asyncio.gather(
        fetch_seismic(),
        fetch_flood(),
        fetch_protected(),
        fetch_thinkhazard(),
        return_exceptions=True
    )

    # Store results
    for name, data in [
        ("seismic_hazard", seismic),
        ("flood_hazard", flood),
        ("protected_areas", protected),
        ("thinkhazard", think)
    ]:
        if isinstance(data, Exception):
            results["errors"][name] = str(data)
        elif isinstance(data, dict) and "error" in data:
            results["errors"][name] = data["error"]
            results[name] = data  # Still store partial data if available
        else:
            results[name] = data

    return results


def format_climate_hazard_summary(hazard_data: Dict[str, Any]) -> str:
    """Format combined hazard API data as a concise summary string."""
    if not hazard_data:
        return "Climate Hazard APIs: QUERY FAILED"

    lines = []

    # Seismic
    seismic = hazard_data.get("seismic_hazard", {})
    if seismic and "error" not in seismic:
        lines.append(f"Seismic: {seismic.get('risk_label', 'N/A')} (PGA {seismic.get('pga_g', 'N/A')}g)")
    else:
        lines.append("Seismic: Query failed")

    # Flood
    flood = hazard_data.get("flood_hazard", {})
    if flood and "error" not in flood:
        lines.append(f"Flood: {flood.get('flood_risk_category', 'N/A')}")
    else:
        lines.append("Flood: Query failed")

    # Protected Areas
    protected = hazard_data.get("protected_areas", {})
    if protected and "error" not in protected:
        if protected.get("inside_protected_area"):
            lines.append(f"Protected Area: INSIDE {protected.get('area_name', 'Unknown')}")
        else:
            nearest = protected.get("nearest_protected_area")
            dist = protected.get("distance_to_nearest_protected_area_km")
            if nearest and dist:
                lines.append(f"Protected Area: {dist}km to {nearest}")
            else:
                lines.append("Protected Area: None nearby")
    else:
        lines.append("Protected Area: Query failed")

    # ThinkHazard
    think = hazard_data.get("thinkhazard", {})
    if think and "error" not in think:
        lines.append(f"ThinkHazard: Flood={think.get('flood', 'N/A')}, EQ={think.get('earthquake', 'N/A')}, Cyclone={think.get('cyclone', 'N/A')}")
    else:
        lines.append("ThinkHazard: Query failed")

    return " | ".join(lines)


if __name__ == "__main__":
    import json

    test_coords = [
        (33.405528, -79.983507, "Russellville, SC"),
    ]

    for lat, lon, name in test_coords:
        print(f"\n{'='*60}")
        print(f"Querying ALL Climate Hazards for {name} ({lat}, {lon})...")
        print("="*60)

        result = asyncio.run(query_all_climate_hazards(lat, lon))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nSummary: {format_climate_hazard_summary(result)}")
