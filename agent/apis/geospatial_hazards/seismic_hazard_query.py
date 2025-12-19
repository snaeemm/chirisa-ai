#!/usr/bin/env python3
"""
Seismic Hazard Query Module (Global PGA Data)

Queries seismic hazard data (Peak Ground Acceleration) for given coordinates.
Uses multiple sources:
1. USGS Design Maps API (US locations) - most accurate for US
2. GEM Global Seismic Hazard Map (worldwide) - via OpenQuake

Returns: PGA in g, risk label (Low/Moderate/High), return period, dataset info

Auth: None required (public APIs)
"""
import requests
from typing import Dict, Any, Optional


# Risk classification bins (per client spec)
def classify_risk(pga_g: float) -> str:
    """
    Classify seismic risk based on PGA value.
    <=0.1g = Low, 0.1-0.2g = Moderate, >0.2g = High
    """
    if pga_g <= 0.1:
        return "Low"
    elif pga_g <= 0.2:
        return "Moderate"
    else:
        return "High"


def query_usgs_hazard(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Query USGS National Seismic Hazard Model for US locations.
    Uses the USGS Design Maps web service.

    Returns PGA for 10% probability of exceedance in 50 years (approx 475-year return period).
    """
    # USGS Design Maps API endpoint
    # Reference: https://earthquake.usgs.gov/ws/designmaps/
    url = "https://earthquake.usgs.gov/ws/designmaps/asce7-22.json"

    params = {
        "latitude": lat,
        "longitude": lon,
        "riskCategory": "II",  # Standard occupancy
        "siteClass": "D",      # Stiff soil (default)
        "title": "HazardQuery",
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            response_data = data.get("response", {}).get("data", {})

            # PGA is given as a fraction of g
            pga = response_data.get("pga")
            if pga is not None:
                return {
                    "pga_g": round(float(pga), 4),
                    "source": "USGS",
                    "model": "ASCE 7-22",
                    "return_period": "2% in 50 years (MCEr)",
                }

            # Alternative: estimate PGA from short-period spectral acceleration (Ss)
            ss = response_data.get("ss")  # Short period spectral acceleration at T=0.2s
            if ss is not None:
                # Conversion: PGA ~ 0.4 x Ss
                # Engineering basis: ASCE 7 design spectrum starts at 0.4xSDS at T=0 (PGA)
                # and rises to SDS at the short-period plateau. Standard spectral
                # amplification factor is 2.5 for 5% damped spectra (SDS/PGA ~ 2.5).
                # Reference: ASCE 7-22 Section 11.4.5, Lubkowski & Aluisi (WCEE 2012)
                estimated_pga = float(ss) * 0.4
                return {
                    "pga_g": round(estimated_pga, 4),
                    "source": "USGS (estimated from Ss)",
                    "model": "ASCE 7-22",
                    "return_period": "2% in 50 years (MCEr)",
                }
    except requests.exceptions.RequestException:
        pass
    except (KeyError, ValueError, TypeError):
        pass

    return None


def query_usgs_probabilistic(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Query USGS Probabilistic Seismic Hazard via the hazard tool API.
    Alternative endpoint for more direct PGA values.
    """
    # Try the NSHM hazard endpoint
    url = "https://earthquake.usgs.gov/nshmp-haz-ws/hazard"

    params = {
        "latitude": lat,
        "longitude": lon,
        "vs30": 760,  # Reference rock velocity
        "edition": "E2014",  # 2014 NSHM
        "imt": "PGA",
        "returnPeriod": 475,  # 10% in 50 years
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            # Extract PGA from response
            curves = data.get("response", [])
            if curves:
                for curve in curves:
                    if curve.get("imt") == "PGA":
                        # Find value at return period
                        hazard = curve.get("data", {})
                        pga_value = hazard.get("yValues", [None])[0]
                        if pga_value:
                            return {
                                "pga_g": round(float(pga_value), 4),
                                "source": "USGS NSHM",
                                "model": "2014 NSHM",
                                "return_period": "10% in 50 years",
                            }
    except Exception:
        pass

    return None


def query_gem_hazard(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Query GEM Global Seismic Hazard Map via WMS GetFeatureInfo.
    Uses the OpenQuake Map Viewer WMS service.

    Returns PGA with 10% probability of exceedance in 50 years,
    computed for reference rock conditions (Vs30 = 760-800 m/s).
    """
    # GEM OpenQuake WMS endpoint
    wms_url = "https://maps.openquake.org/mapproxy/ghm/wms"

    # Build a small bounding box around the point for WMS query
    half_size = 0.5
    bbox = f"{lon - half_size},{lat - half_size},{lon + half_size},{lat + half_size}"

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": "seismic-hazard-pga-g",
        "QUERY_LAYERS": "seismic-hazard-pga-g",
        "INFO_FORMAT": "application/json",
        "SRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": 256,
        "HEIGHT": 256,
        "X": 128,  # Center of the image
        "Y": 128,
    }

    try:
        resp = requests.get(wms_url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()

            # Parse GeoJSON response
            features = data.get("features", [])
            if features:
                props = features[0].get("properties", {})
                # PGA is in "Band 1" property
                pga_str = props.get("Band 1")
                if pga_str:
                    pga_value = float(pga_str)
                    return {
                        "pga_g": round(pga_value, 4),
                        "source": "GEM Global Seismic Hazard Map",
                        "model": "GEM GSHM v2023.1",
                        "return_period": "10% in 50 years",
                        "site_conditions": "Reference rock (Vs30 = 760-800 m/s)",
                    }
    except Exception:
        pass

    return None


def get_fallback_estimate(lat: float, lon: float, country: str = None) -> Dict[str, Any]:
    """
    Provide a conservative fallback estimate based on general seismic zones.
    This is used when APIs are unavailable.

    Note: These are rough estimates for screening purposes only.
    Based on GSHAP and GEM regional data.
    """
    # Moderate seismicity regions - PGA 0.1-0.2g (check FIRST to avoid overlap)
    moderate_seismicity_regions = [
        # Arabian Peninsula (moderate - NOT in Zagros belt)
        (20, 32, 44, 55),      # Saudi Arabia (eastern), UAE, Qatar, Bahrain, Kuwait
        # Southern Europe
        (35, 45, 5, 20),       # Italy, Greece
        (35, 40, -10, 5),      # Spain, Portugal
        # East Africa Rift
        (-15, 15, 25, 45),     # East Africa
        # India (away from Himalayas)
        (8, 25, 72, 88),       # Peninsular India
        # Central/Eastern Europe
        (45, 56, 5, 25),       # Central Europe including Poland
        # Eastern Mediterranean (lower risk areas)
        (30, 36, 33, 40),      # Jordan, Israel (southern)
    ]

    # High seismicity regions (Ring of Fire, Alpine-Himalayan belt) - PGA > 0.2g
    high_seismicity_regions = [
        # Pacific Ring of Fire
        (30, 45, 125, 150),    # Japan
        (-10, 10, 95, 140),    # Indonesia
        (5, 25, 120, 130),     # Philippines
        (-45, -15, -80, -65),  # Chile
        (30, 45, -125, -115),  # US West Coast
        (32, 42, -125, -110),  # California/Nevada
        # Mediterranean/Middle East - HIGH zones (specific)
        (36, 42, 26, 45),      # Turkey
        (27, 40, 55, 65),      # Iran (Zagros belt - EAST of lon 55)
        (38, 43, 40, 50),      # Caucasus
        (25, 38, 60, 78),      # Afghanistan, Pakistan
        (26, 35, 75, 92),      # Nepal/Himalayan front
        # Central America
        (5, 20, -92, -75),     # Central America, Caribbean
    ]

    # Check MODERATE regions first (more specific boundaries)
    for lat_min, lat_max, lon_min, lon_max in moderate_seismicity_regions:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return {
                "pga_g": 0.15,  # Moderate estimate
                "risk_category": "Moderate",
                "source": "Regional estimate (moderate seismicity zone)",
                "model": "Fallback estimate based on GSHAP/GEM zones",
                "return_period": "~10% in 50 years (estimated)",
                "note": "API unavailable - using regional estimate. Verify with local data.",
            }

    # Then check HIGH regions
    for lat_min, lat_max, lon_min, lon_max in high_seismicity_regions:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return {
                "pga_g": 0.25,  # Conservative high estimate
                "risk_category": "High",
                "source": "Regional estimate (high seismicity zone)",
                "model": "Fallback estimate based on GSHAP/GEM zones",
                "return_period": "~10% in 50 years (estimated)",
                "note": "API unavailable - using regional estimate. Verify with local data.",
            }

    # Low seismicity (stable continental interiors)
    return {
        "pga_g": 0.05,  # Low estimate for stable regions
        "risk_category": "Low",
        "source": "Regional estimate (low seismicity / stable region)",
        "model": "Fallback estimate based on GSHAP/GEM zones",
        "return_period": "~10% in 50 years (estimated)",
        "note": "API unavailable - using regional estimate. Verify with local data.",
    }


def query_seismic_hazard(lat: float, lon: float) -> Dict[str, Any]:
    """
    Query seismic hazard (PGA) for given coordinates.

    Tries multiple sources in order:
    1. USGS Design Maps (for US locations)
    2. GEM Global Hazard Map (worldwide)
    3. Fallback regional estimate

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Dictionary with:
        - pga_g: float (peak ground acceleration in g)
        - risk_label: str (Low / Moderate / High)
        - return_period: str (probability description)
        - dataset_vintage: str
        - data_source: str
    """
    result = {
        "pga_g": None,
        "risk_label": None,
        "return_period": None,
        "return_period_years": None,
        "comparable_across_regions": True,
        "dataset_vintage": None,
        "data_source": None,
        "data_confidence": None,
    }

    # Check if location is in US (roughly)
    is_us = (24 <= lat <= 50 and -125 <= lon <= -66) or \
            (18 <= lat <= 22 and -160 <= lon <= -154) or \
            (51 <= lat <= 72 and -180 <= lon <= -130)

    hazard_data = None

    # Try USGS first for US locations
    if is_us:
        hazard_data = query_usgs_hazard(lat, lon)
        if not hazard_data:
            hazard_data = query_usgs_probabilistic(lat, lon)

    # Try GEM for non-US or if USGS failed
    if not hazard_data:
        hazard_data = query_gem_hazard(lat, lon)

    # Use fallback if all APIs fail
    if not hazard_data:
        hazard_data = get_fallback_estimate(lat, lon)

    # Build result
    if hazard_data:
        pga = hazard_data.get("pga_g", 0)
        source = hazard_data.get("source", "Unknown")

        result["pga_g"] = pga
        result["risk_label"] = classify_risk(pga)
        result["return_period"] = hazard_data.get("return_period", "10% in 50 years")
        result["data_source"] = source
        result["model"] = hazard_data.get("model")

        # Set dataset_vintage with explicit date based on source
        model = hazard_data.get("model", "")
        if "ASCE 7-22" in model:
            result["dataset_vintage"] = "2022 (USGS NSHM 2018 / ASCE 7-22)"
        elif "GEM GSHM v2023" in model:
            result["dataset_vintage"] = "2023 (GEM Global Seismic Hazard Map v2023.1)"
        elif "2014 NSHM" in model:
            result["dataset_vintage"] = "2014 (USGS NSHM 2014)"
        elif "Fallback" in model or "estimate" in model.lower():
            result["dataset_vintage"] = "N/A (Regional estimate based on GSHAP/GEM zones)"
        else:
            result["dataset_vintage"] = model if model else "Unknown"

        # Set return period comparability metadata and data confidence
        # US (USGS) uses 2% in 50 years (~2475-year), International (GEM) uses 10% in 50 years (~475-year)
        if "USGS" in source and "estimated" not in source.lower():
            result["return_period_years"] = 2475
            result["comparable_across_regions"] = False
            result["comparability_note"] = "US data uses MCEr (2% in 50 years, ~2475-year). International uses 10% in 50 years (~475-year). PGA values not directly comparable across regions."
            result["data_confidence"] = "high"
        elif "USGS" in source and "estimated" in source.lower():
            result["return_period_years"] = 2475
            result["comparable_across_regions"] = False
            result["comparability_note"] = "US data uses MCEr (2% in 50 years, ~2475-year). International uses 10% in 50 years (~475-year). PGA values not directly comparable across regions."
            result["data_confidence"] = "medium"  # Estimated from Ss
        elif "GEM" in source:
            result["return_period_years"] = 475
            result["comparable_across_regions"] = True  # GEM is consistent worldwide
            result["data_confidence"] = "high"
        else:
            # Fallback estimates
            result["return_period_years"] = 475
            result["comparable_across_regions"] = False
            result["comparability_note"] = "Regional estimate; verify with local seismic studies."
            result["data_confidence"] = "low"

        if hazard_data.get("note"):
            result["note"] = hazard_data["note"]

    return result


def format_human_summary(res: Dict[str, Any]) -> str:
    """Format results as human-readable summary."""
    pga = res.get("pga_g", "N/A")
    risk = res.get("risk_label", "Unknown")
    source = res.get("data_source", "Unknown")
    period = res.get("return_period", "N/A")

    summary = (
        f"Seismic Hazard Assessment:\n"
        f"  PGA: {pga}g\n"
        f"  Risk Level: {risk}\n"
        f"  Return Period: {period}\n"
        f"  Source: {source}"
    )

    if res.get("note"):
        summary += f"\n  Note: {res['note']}"

    return summary


if __name__ == "__main__":
    import json

    test_coords = [
        (33.405528, -79.983507, "Russellville, SC"),
        (51.0530, 16.1921, "Jawor, Poland"),
        (26.3097274, 49.8100201, "Dammam, KSA"),
    ]

    for lat, lon, name in test_coords:
        print(f"\n{'='*60}")
        print(f"Querying Seismic Hazard for {name} ({lat}, {lon})...")
        print("="*60)

        result = query_seismic_hazard(lat, lon)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\nHuman summary:")
        print(format_human_summary(result))
