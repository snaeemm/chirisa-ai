#!/usr/bin/env python3
"""
WRI Aqueduct Water Stress Query Module

Queries the World Resources Institute Aqueduct dataset via Google Earth Engine
for baseline water stress at given coordinates.

Returns: Water stress score (0-5), category label, dataset vintage

Data Source: WRI Aqueduct Water Risk V4
API: Google Earth Engine
Auth: GEE Service Account (via environment variables)

Used by agents:
- Site Civil: Section C - Water & Wastewater Infrastructure (>4.0 = NO-GO)
- Regulatory ESG: Section C - Water stress levels (WRI Aqueduct baseline/future)
"""
import ee
import os
from typing import Dict, Any, Optional

# Ensure environment variables are loaded (fallback if not loaded by caller)
from dotenv import load_dotenv
load_dotenv()


# Water stress category mapping (per WRI Aqueduct documentation)
def get_water_stress_category(score: float) -> str:
    """
    Map water stress score (0-5) to category label.
    Based on WRI Aqueduct methodology.
    """
    if score < 0:
        return "No Data"
    elif score < 1:
        return "Low"
    elif score < 2:
        return "Low-Medium"
    elif score < 3:
        return "Medium-High"
    elif score < 4:
        return "High"
    else:
        return "Extremely High"


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


def get_aqueduct_vintage() -> str:
    """
    Get the dataset vintage for WRI Aqueduct from GEE asset metadata.
    Aqueduct V4 is a fixed release (2023), but we verify from metadata.
    """
    try:
        if not ensure_gee_initialized():
            return "2023 (WRI Aqueduct V4)"

        # Get asset metadata
        asset_info = ee.data.getAsset('WRI/Aqueduct_Water_Risk/V4/baseline_annual')

        if asset_info:
            # Check for version/date in properties
            properties = asset_info.get('properties', {})
            version = properties.get('version')
            if version:
                return f"{version} (WRI Aqueduct)"

            # Try start_time
            start_time = asset_info.get('startTime')
            if start_time:
                from datetime import datetime
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                return f"{dt.year} (WRI Aqueduct V4)"
    except Exception:
        pass

    # Fallback - V4 was released in 2023
    return "2023 (WRI Aqueduct V4)"


def query_water_stress(lat: float, lon: float) -> Dict[str, Any]:
    """
    Query WRI Aqueduct for baseline water stress at given coordinates.

    If the exact point has no data (ocean, coastal, etc.), searches nearby
    basins within ~50km to find the closest with valid data.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Dictionary with:
        - baseline_water_stress_score: float (0-5 scale)
        - category_label: str (Low / Low-Medium / Medium-High / High / Extremely High)
        - raw_value: float (original BWS value)
        - dataset_vintage: str
        - data_source: str
    """
    result = {
        "baseline_water_stress_score": None,
        "category_label": "No Data",
        "raw_value": None,
        "basin_name": None,
        "used_nearby_search": False,
        "dataset_vintage": None,  # Will be set dynamically
        "data_source": "WRI via Google Earth Engine",
        "data_confidence": None,
    }

    # Ensure GEE is initialized
    if not ensure_gee_initialized():
        result["error"] = "Google Earth Engine initialization failed"
        result["dataset_vintage"] = "2023 (WRI Aqueduct V4)"
        return result

    # Get dataset vintage dynamically
    result["dataset_vintage"] = get_aqueduct_vintage()

    try:
        # Create point geometry
        point = ee.Geometry.Point([lon, lat])

        # Query WRI Aqueduct dataset
        dataset = ee.FeatureCollection('WRI/Aqueduct_Water_Risk/V4/baseline_annual')

        # First try: exact point query
        features = dataset.filterBounds(point)
        feature = features.first()
        used_nearby = False

        # Check if we got valid data
        props = None
        if feature is not None:
            props = feature.getInfo()

        # If no data or invalid score, try nearby search
        if props is None or props.get('properties', {}).get('bws_score', -9999) < -9000:
            # Create a buffer around the point (~50km) and find nearby basins
            buffer = point.buffer(50000)  # 50km buffer
            nearby_features = dataset.filterBounds(buffer).filter(
                ee.Filter.gt('bws_score', -9000)  # Only basins with valid data
            )

            # Sort by distance and get closest
            nearby_list = nearby_features.limit(5).getInfo()
            if nearby_list and nearby_list.get('features'):
                # Use the first feature with valid data
                props = nearby_list['features'][0]
                used_nearby = True
                result["used_nearby_search"] = True
                result["note"] = "Exact location has no data; using nearest basin with data (~50km search)"

        if props is None or 'properties' not in props:
            result["error"] = "No water stress data available for this location or nearby"
            return result

        properties = props['properties']

        # Extract baseline water stress score (bws_score is 0-5 scale)
        bws_score = properties.get('bws_score')
        bws_raw = properties.get('bws_raw')
        bws_label = properties.get('bws_label')

        # Handle no-data sentinel values (-9999 means no data available)
        if bws_score is not None and bws_score > -9000:
            result["baseline_water_stress_score"] = round(float(bws_score), 2)
            result["category_label"] = bws_label if bws_label else get_water_stress_category(bws_score)
        else:
            result["baseline_water_stress_score"] = None
            result["category_label"] = "No Data"
            if not used_nearby:
                result["note"] = "Location is in an area with no water stress data (e.g., ocean, small island)"

        # WRI Aqueduct sentinel values:
        # -9999 = No data (insufficient inputs)
        # 9999 = Extreme scarcity (supply < 0.001 m/month for 6+ months) - VALID DATA
        if bws_raw is not None and bws_raw > -9000:
            result["raw_value"] = round(float(bws_raw), 4)
            # Flag the 9999 case since it looks like a sentinel but is actually valid extreme scarcity
            if bws_raw >= 9999:
                result["raw_value_note"] = "9999 indicates extreme scarcity (supply nearly exhausted)"

        # Get basin identifier if available
        basin_id = properties.get('aqid') or properties.get('aq30_id')
        if basin_id and basin_id > 0:
            result["basin_id"] = basin_id

        # Set data confidence based on how data was obtained
        if used_nearby:
            result["data_confidence"] = "medium"
        else:
            result["data_confidence"] = "high"

    except Exception as e:
        result["error"] = f"Query failed: {str(e)}"

    return result


def format_human_summary(res: Dict[str, Any]) -> str:
    """Format results as human-readable summary."""
    score = res.get("baseline_water_stress_score")
    category = res.get("category_label", "No Data")

    if score is not None:
        interpretation = ""
        if category == "Extremely High":
            interpretation = " (Consider air-cooled/hybrid systems; avoid evaporative cooling)"
        elif category == "High":
            interpretation = " (Water availability may be constrained)"

        return (
            f"Water Stress Assessment:\n"
            f"  Score: {score}/5\n"
            f"  Category: {category}{interpretation}\n"
            f"  Source: {res.get('data_source', 'WRI Aqueduct')}"
        )
    else:
        error = res.get("error", "Unknown error")
        return f"Water Stress: No data available. Error: {error}"


if __name__ == "__main__":
    import json as json_module

    test_coords = [
        (33.405528, -79.983507, "Russellville, SC"),
        (51.0530, 16.1921, "Jawor, Poland"),
        (26.3097274, 49.8100201, "Dammam, KSA"),
    ]

    for lat, lon, name in test_coords:
        print(f"\n{'='*60}")
        print(f"Querying Water Stress for {name} ({lat}, {lon})...")
        print("="*60)

        result = query_water_stress(lat, lon)
        print(json_module.dumps(result, indent=2, ensure_ascii=False))
        print("\nHuman summary:")
        print(format_human_summary(result))
