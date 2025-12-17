#!/usr/bin/env python3
"""
Global Flood Hazard Query Module

Queries Open-Meteo Flood API (powered by GloFAS - Global Flood Awareness System)
for river discharge data and flood risk indicators at given coordinates.

Returns: River discharge stats, flood risk indicators, historical extremes

Data Source: Open-Meteo Flood API (GloFAS v4)
Coverage: Global, 5km resolution
Historical: 1984 - present
Forecast: Up to 7 months ahead
API: Free, no key required
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import statistics

# API Endpoint
FLOOD_API_URL = "https://flood-api.open-meteo.com/v1/flood"


def get_flood_risk_category(discharge: float, mean_discharge: float) -> str:
    """
    Categorize flood risk based on current discharge vs historical mean.

    This is a simplified risk assessment. In practice, flood risk depends on
    local channel capacity, infrastructure, etc.
    """
    if mean_discharge <= 0 or discharge <= 0:
        return "Unknown"

    ratio = discharge / mean_discharge

    if ratio < 1.5:
        return "Low"
    elif ratio < 3.0:
        return "Moderate"
    elif ratio < 5.0:
        return "High"
    elif ratio < 10.0:
        return "Very High"
    else:
        return "Extreme"


def query_flood_hazard(lat: float, lon: float, include_forecast: bool = True) -> Dict[str, Any]:
    """
    Query Open-Meteo Flood API for river discharge and flood risk data.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        include_forecast: Whether to include 3-month forecast data

    Returns:
        Dictionary with:
        - current_discharge_m3s: Current river discharge (m3/s)
        - historical_mean_m3s: Historical average discharge
        - historical_max_m3s: Historical maximum discharge
        - flood_risk_category: Risk assessment (Low/Moderate/High/Very High/Extreme)
        - forecast_max_m3s: Maximum forecasted discharge (if requested)
        - percentile_90_m3s: 90th percentile discharge (flood threshold proxy)
        - data_source: API source info
    """
    # Get current date for dynamic vintage
    current_date = datetime.now()
    current_year = current_date.year
    current_quarter = (current_date.month - 1) // 3 + 1

    result = {
        "current_discharge_m3s": None,
        "historical_mean_m3s": None,
        "historical_max_m3s": None,
        "historical_min_m3s": None,
        "percentile_90_m3s": None,
        "percentile_99_m3s": None,
        "flood_risk_category": "Unknown",
        "forecast_max_m3s": None,
        "forecast_period_days": None,
        "river_found": False,
        "dataset_vintage": f"{current_year}-Q{current_quarter} (GloFAS v4, real-time)",
        "data_source": "Open-Meteo Flood API (GloFAS v4)",
        "data_coverage": "Global, 5km resolution",
        "historical_period": "1984-present",
        "data_confidence": "high",
    }

    try:
        # Step 1: Get forecast data (includes recent past + forecast)
        forecast_params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "river_discharge",
            "past_days": 92,  # ~3 months of recent history
            "forecast_days": 92,  # ~3 months forecast
        }

        response = requests.get(FLOOD_API_URL, params=forecast_params, timeout=30)
        response.raise_for_status()
        forecast_data = response.json()

        # Step 2: Get historical data separately (using archive endpoint)
        # Calculate date range for historical data (10 years)
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=365 * 10)

        historical_url = "https://archive-api.open-meteo.com/v1/archive"
        historical_params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": "river_discharge",
        }

        # Try historical API (may not have river discharge for all locations)
        historical_discharges = []
        try:
            hist_response = requests.get(historical_url, params=historical_params, timeout=30)
            if hist_response.status_code == 200:
                hist_data = hist_response.json()
                if "daily" in hist_data and "river_discharge" in hist_data["daily"]:
                    historical_discharges = [d for d in hist_data["daily"]["river_discharge"]
                                            if d is not None and d >= 0]
        except:
            pass  # Historical data is optional

        # Check if we got valid forecast data
        if "daily" not in forecast_data or "river_discharge" not in forecast_data["daily"]:
            result["error"] = "No river data available at this location"
            result["note"] = "Location may be far from any significant river (>5km resolution)"
            return result

        discharges = forecast_data["daily"]["river_discharge"]
        dates = forecast_data["daily"]["time"]

        # Filter out None values
        valid_discharges = [d for d in discharges if d is not None and d >= 0]

        if not valid_discharges:
            result["error"] = "No valid discharge data available"
            return result

        result["river_found"] = True

        # Use historical data if available, otherwise use recent data
        stats_discharges = historical_discharges if historical_discharges else valid_discharges

        # Calculate statistics
        result["historical_mean_m3s"] = round(statistics.mean(stats_discharges), 2)
        result["historical_max_m3s"] = round(max(stats_discharges), 2)
        result["historical_min_m3s"] = round(min(stats_discharges), 2)

        # Calculate percentiles for flood thresholds
        sorted_discharges = sorted(stats_discharges)
        n = len(sorted_discharges)
        if n >= 10:
            result["percentile_90_m3s"] = round(sorted_discharges[int(n * 0.90)], 2)
            result["percentile_99_m3s"] = round(sorted_discharges[min(int(n * 0.99), n-1)], 2)

        # Find today's index in the data
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_idx = None
        for i, d in enumerate(dates):
            if d == today_str:
                today_idx = i
                break

        # Get current discharge
        if today_idx is not None and discharges[today_idx] is not None:
            result["current_discharge_m3s"] = round(discharges[today_idx], 2)
        elif valid_discharges:
            # Use most recent valid value
            result["current_discharge_m3s"] = round(valid_discharges[-1], 2)

        if result["current_discharge_m3s"]:
            result["flood_risk_category"] = get_flood_risk_category(
                result["current_discharge_m3s"],
                result["historical_mean_m3s"]
            )

        # Get forecast max (future dates only)
        if include_forecast and today_idx is not None:
            future_discharges = [d for d in discharges[today_idx:] if d is not None and d >= 0]
            if future_discharges:
                result["forecast_max_m3s"] = round(max(future_discharges), 2)
                result["forecast_period_days"] = len(future_discharges)

                # Check if forecast exceeds 90th percentile (flood warning)
                if result["percentile_90_m3s"] and result["forecast_max_m3s"] > result["percentile_90_m3s"]:
                    result["flood_warning"] = True
                    result["flood_warning_note"] = f"Forecast discharge ({result['forecast_max_m3s']} m3/s) exceeds 90th percentile ({result['percentile_90_m3s']} m3/s)"

        # Add interpretation based on mean discharge
        mean = result["historical_mean_m3s"]
        if mean > 1000:
            result["river_size"] = "Major river"
        elif mean > 100:
            result["river_size"] = "Medium river"
        elif mean > 10:
            result["river_size"] = "Small river"
        else:
            result["river_size"] = "Stream/creek"

        # Flag if using limited historical data
        if not historical_discharges:
            result["note"] = "Using ~6 months of recent data for statistics (historical archive unavailable)"

    except requests.exceptions.RequestException as e:
        result["error"] = f"API request failed: {str(e)}"
    except Exception as e:
        result["error"] = f"Query failed: {str(e)}"

    return result


def format_human_summary(res: Dict[str, Any]) -> str:
    """Format results as human-readable summary."""
    if not res.get("river_found"):
        return f"Flood Hazard: No significant river found at this location.\n  Note: {res.get('note', 'N/A')}"

    lines = [
        "Flood Hazard Assessment:",
        f"  River Size: {res.get('river_size', 'Unknown')}",
        f"  Current Discharge: {res.get('current_discharge_m3s', 'N/A')} m3/s",
        f"  Historical Mean: {res.get('historical_mean_m3s', 'N/A')} m3/s",
        f"  Historical Max: {res.get('historical_max_m3s', 'N/A')} m3/s",
        f"  90th Percentile: {res.get('percentile_90_m3s', 'N/A')} m3/s",
        f"  Flood Risk: {res.get('flood_risk_category', 'Unknown')}",
    ]

    if res.get("flood_warning"):
        lines.append(f"  WARNING: {res.get('flood_warning_note')}")

    if res.get("forecast_max_m3s"):
        lines.append(f"  Forecast Max (3mo): {res['forecast_max_m3s']} m3/s")

    lines.append(f"  Source: {res.get('data_source', 'Open-Meteo')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import json

    test_coords = [
        (33.405528, -79.983507, "Russellville, SC"),
        (51.0530, 16.1921, "Jawor, Poland"),
        (26.3097274, 49.8100201, "Dammam, KSA"),
    ]

    for lat, lon, name in test_coords:
        print(f"\n{'='*60}")
        print(f"Querying Flood Hazard for {name} ({lat}, {lon})...")
        print("="*60)

        result = query_flood_hazard(lat, lon)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\nHuman summary:")
        print(format_human_summary(result))
