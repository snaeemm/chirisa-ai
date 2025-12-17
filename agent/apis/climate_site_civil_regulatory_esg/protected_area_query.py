#!/usr/bin/env python3
"""
WDPA Protected Areas Query Module

Queries the World Database on Protected Areas (WDPA) via Google Earth Engine
to check if coordinates fall within a protected/conservation area.

Returns: Inside protected area (yes/no), area name, IUCN category, distance to boundary

Data Source: WCMC/WDPA (World Database on Protected Areas)
API: Google Earth Engine
Auth: GEE Service Account (via environment variables)

Used by agents:
- Climate (Hazards): Section D - Protected Areas & Environmental Constraints
- Site Civil: NO-GO Gate #1 - Protected Land / Zoning Incompatibility
- Regulatory ESG: Section C - Biodiversity and protected area constraints
"""
import ee
import os
from typing import Dict, Any, Optional

# Ensure environment variables are loaded (fallback if not loaded by caller)
from dotenv import load_dotenv
load_dotenv()


def initialize_gee() -> bool:
    """
    Initialize Google Earth Engine with service account credentials.
    Credentials are loaded from environment variables for Streamlit secrets compatibility.

    Required env vars:
    - GEE_SERVICE_ACCOUNT_EMAIL: Service account email
    - GEE_PRIVATE_KEY: Private key (with escaped newlines)
    - GEE_PROJECT_ID: GCP project ID (optional)
    """
    try:
        service_account = os.getenv('GEE_SERVICE_ACCOUNT_EMAIL')
        private_key = os.getenv('GEE_PRIVATE_KEY')
        project_id = os.getenv('GEE_PROJECT_ID')

        if not service_account or not private_key:
            print("Warning: GEE credentials not found in environment variables")
            print("  Required: GEE_SERVICE_ACCOUNT_EMAIL, GEE_PRIVATE_KEY")
            return False

        # Handle escaped newlines in private key (from .env files)
        private_key = private_key.replace('\\n', '\n')

        credentials = ee.ServiceAccountCredentials(
            service_account,
            key_data=private_key
        )
        ee.Initialize(credentials, project=project_id)
        return True
    except Exception as e:
        print(f"GEE initialization failed: {e}")
        return False


# Initialize GEE on module load
_gee_initialized = False


def ensure_gee_initialized():
    """Ensure GEE is initialized before making queries."""
    global _gee_initialized
    if not _gee_initialized:
        _gee_initialized = initialize_gee()
    return _gee_initialized


def get_wdpa_vintage() -> str:
    """
    Get the dataset vintage for WDPA from GEE asset metadata.
    WDPA is updated monthly, so we fetch the actual version date.
    Falls back to a descriptive string if metadata unavailable.
    """
    try:
        if not ensure_gee_initialized():
            return "WDPA (monthly release)"

        # Get asset metadata for WDPA
        asset_info = ee.data.getAsset('WCMC/WDPA/current/polygons')

        # Try to extract version/date from metadata
        if asset_info:
            # Check for version in properties or description
            properties = asset_info.get('properties', {})
            version = properties.get('version') or properties.get('date_range')
            if version:
                return f"{version} (WDPA)"

            # Try start_time which indicates data vintage
            start_time = asset_info.get('startTime')
            if start_time:
                # Format: 2024-01-01T00:00:00Z -> 2024-Q1
                from datetime import datetime
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                quarter = (dt.month - 1) // 3 + 1
                return f"{dt.year}-Q{quarter} (WDPA)"
    except Exception:
        pass

    return "WDPA (monthly release)"


def query_protected_area(lat: float, lon: float) -> Dict[str, Any]:
    """
    Check if coordinates fall within a protected area using WDPA data.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Dictionary with:
        - inside_protected_area: bool (True if inside)
        - area_name: str or None (name of protected area)
        - iucn_category: str or None (IUCN management category)
        - designation: str or None (type of protected area)
        - distance_to_boundary_km: float or None (if not inside, distance to nearest)
        - dataset_vintage: str
    """
    result = {
        "inside_protected_area": False,
        "area_name": None,
        "iucn_category": None,
        "designation": None,
        "status": None,
        "dataset_vintage": None,  # Will be set dynamically
        "data_source": "WCMC/WDPA via Google Earth Engine",
        "data_confidence": "high",  # WDPA is authoritative source
    }

    # Ensure GEE is initialized
    if not ensure_gee_initialized():
        result["error"] = "Google Earth Engine initialization failed"
        result["dataset_vintage"] = "WDPA (monthly release)"
        return result

    # Get dataset vintage dynamically
    result["dataset_vintage"] = get_wdpa_vintage()

    try:
        # Create point geometry
        point = ee.Geometry.Point([lon, lat])

        # Query WDPA polygons dataset
        wdpa = ee.FeatureCollection('WCMC/WDPA/current/polygons')

        # First check: Is the point inside any protected area?
        containing_areas = wdpa.filterBounds(point)
        count = containing_areas.size().getInfo()

        if count > 0:
            # Point is inside a protected area
            result["inside_protected_area"] = True

            # Get the first (smallest/most specific) protected area containing the point
            # Sort by area to get the most specific one
            area_info = containing_areas.sort('REP_AREA').first().getInfo()

            if area_info and 'properties' in area_info:
                props = area_info['properties']
                result["area_name"] = props.get('NAME') or props.get('ORIG_NAME')
                result["iucn_category"] = props.get('IUCN_CAT')
                result["designation"] = props.get('DESIG')
                result["status"] = props.get('STATUS')
                result["wdpa_id"] = props.get('WDPAID')
                result["marine"] = "Marine" if props.get('MARINE') == '2' else (
                    "Coastal" if props.get('MARINE') == '1' else "Terrestrial"
                )

                # Get area size
                rep_area = props.get('REP_AREA')
                if rep_area:
                    result["area_km2"] = round(float(rep_area), 2)

            result["distance_to_boundary_km"] = 0  # Inside, so distance is 0

        else:
            # Point is NOT inside any protected area
            result["inside_protected_area"] = False

            # Search for nearby protected areas (within 50km)
            buffer = point.buffer(50000)  # 50km buffer
            nearby_areas = wdpa.filterBounds(buffer)
            nearby_count = nearby_areas.size().getInfo()

            if nearby_count > 0:
                # Find the closest protected area
                # Add distance property to each feature
                def add_distance(feature):
                    centroid = feature.geometry().centroid()
                    distance = centroid.distance(point)
                    return feature.set('distance_to_point', distance)

                nearby_with_distance = nearby_areas.map(add_distance)
                closest = nearby_with_distance.sort('distance_to_point').first().getInfo()

                if closest and 'properties' in closest:
                    props = closest['properties']
                    result["nearest_protected_area"] = props.get('NAME') or props.get('ORIG_NAME')
                    result["nearest_iucn_category"] = props.get('IUCN_CAT')

                    # Calculate distance in km
                    distance_m = props.get('distance_to_point')
                    if distance_m:
                        # Use clearer field name when OUTSIDE a protected area
                        result["distance_to_nearest_protected_area_km"] = round(float(distance_m) / 1000, 2)

    except Exception as e:
        result["error"] = f"Query failed: {str(e)}"

    return result


def format_human_summary(res: Dict[str, Any]) -> str:
    """Format results as human-readable summary."""
    inside = res.get("inside_protected_area", False)

    if inside:
        name = res.get("area_name", "Unknown")
        category = res.get("iucn_category", "Not specified")
        designation = res.get("designation", "")

        return (
            f"Protected Area Assessment:\n"
            f"  INSIDE PROTECTED AREA: YES\n"
            f"  Name: {name}\n"
            f"  IUCN Category: {category}\n"
            f"  Designation: {designation}\n"
            f"  WARNING: Development may be restricted or prohibited"
        )
    else:
        distance = res.get("distance_to_nearest_protected_area_km")
        nearest = res.get("nearest_protected_area")

        summary = "Protected Area Assessment:\n  INSIDE PROTECTED AREA: NO"
        if nearest and distance:
            summary += f"\n  Nearest protected area: {nearest} ({distance} km away)"
        return summary


if __name__ == "__main__":
    import json as json_module

    test_coords = [
        (33.405528, -79.983507, "Russellville, SC"),
        (51.0530, 16.1921, "Jawor, Poland"),
        (26.3097274, 49.8100201, "Dammam, KSA"),
    ]

    for lat, lon, name in test_coords:
        print(f"\n{'='*60}")
        print(f"Querying Protected Areas for {name} ({lat}, {lon})...")
        print("="*60)

        result = query_protected_area(lat, lon)
        print(json_module.dumps(result, indent=2, ensure_ascii=False))
        print("\nHuman summary:")
        print(format_human_summary(result))
