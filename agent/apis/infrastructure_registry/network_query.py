#!/usr/bin/env python3
import requests
import math
import json
import time
import re

# Geocoding is disabled - we use facility coordinates directly from PeeringDB (faster and more accurate)
GEOPY_AVAILABLE = False

# ----------------------------------------------------
# Request Cache
# ----------------------------------------------------
REQUEST_CACHE = {}
CACHE_EXPIRY_SECONDS = 7200  # 2 hours

# ----------------------------------------------------
# Utils
# ----------------------------------------------------
def normalize_carrier_name(name):
    """Strip common corporate suffixes for deduplication."""
    if not name:
        return name
    suffixes = [
        r'\s+Inc\.?$', r'\s+LLC\.?$', r'\s+Ltd\.?$', r'\s+Limited$',
        r'\s+S\.A\.?$', r'\s+Sp\.\s*z\s*o\.?o\.?$', r'\s+Spolka Akcyjna$',
        r'\s+Corporation$', r'\s+Corp\.?$', r'\.$', r',$'
    ]
    normalized = name
    for suffix_pattern in suffixes:
        normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
    return normalized.strip()


def hav(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat/2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon/2)**2
    )
    return 2 * R * math.asin(math.sqrt(a))


def safe_json(url, timeout=30, retry_count=0, max_retries=3, warn_on_empty=True):
    """
    Fetch JSON from URL with exponential backoff for rate limiting.

    Args:
        warn_on_empty: If False, don't print warning for 0 results (useful for ixfac queries
                       where most facilities don't host IXPs)
    """
    try:
        # Progressive delay: 2s, 3s, 5s, 8s based on retry count
        delays = [2, 3, 5, 8]
        delay = delays[min(retry_count, len(delays)-1)]
        time.sleep(delay)

        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        data = r.json()

        # Log empty results only if warn_on_empty is True
        if warn_on_empty and isinstance(data, dict) and "data" in data:
            if len(data["data"]) == 0:
                print(f"  [Warning: Query returned 0 results] {url[:80]}...")

        return data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            if retry_count < max_retries:
                # Exponential backoff: 10s, 20s, 40s
                backoff_time = 10 * (2 ** retry_count)
                print(f"  [Rate limited (attempt {retry_count+1}/{max_retries}), waiting {backoff_time}s...]")
                time.sleep(backoff_time)
                return safe_json(url, timeout, retry_count=retry_count+1, max_retries=max_retries)
            else:
                print(f"  [Rate limit exceeded after {max_retries} retries]")
                return None
        print(f"[Error] {url} -> {e}")
        return None
    except Exception as e:
        print(f"[Error] {url} -> {e}")
        return None


def get_cached_or_fetch(url, timeout=30, warn_on_empty=True):
    """Get from cache if available and not expired, otherwise fetch and cache."""
    now = time.time()

    if url in REQUEST_CACHE:
        cached_data, cached_time = REQUEST_CACHE[url]
        if now - cached_time < CACHE_EXPIRY_SECONDS:
            return cached_data

    # Not cached or expired - fetch fresh
    data = safe_json(url, timeout, warn_on_empty=warn_on_empty)
    if data:
        REQUEST_CACHE[url] = (data, now)
    return data


# ----------------------------------------------------
# Geocoding DISABLED - using PeeringDB facility coordinates directly
# ----------------------------------------------------
CITY_COORD_CACHE = {}


def get_city_coordinates(city, country):
    """
    Get city-level coordinates using Nominatim geocoding.
    Returns (lat, lon) or (None, None) if geocoding fails or geopy not available.
    """
    if not GEOPY_AVAILABLE or not geolocator:
        return (None, None)

    cache_key = f"{city},{country}"
    if cache_key in CITY_COORD_CACHE:
        return CITY_COORD_CACHE[cache_key]

    try:
        time.sleep(0.5)  # Reduced from 1s - Nominatim allows 1 req/sec, 0.5s is safer with some margin
        location = geolocator.geocode(f"{city}, {country}", timeout=5)
        if location:
            coords = (location.latitude, location.longitude)
            CITY_COORD_CACHE[cache_key] = coords
            return coords
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"  [Geocoding error for {city}, {country}: {e}]")

    CITY_COORD_CACHE[cache_key] = (None, None)
    return (None, None)


def validate_facility_distance(query_lat, query_lon, facility_lat, facility_lon,
                                city, country, threshold_km=100, enable_geocoding=True):
    """
    Validate facility coordinates against city-level geocoding.
    Returns (distance_km, distance_method).

    If facility coords differ from city coords by >threshold_km, use city fallback.
    Set enable_geocoding=False to skip geocoding validation (faster but less accurate).
    """
    fac_dist = hav(query_lat, query_lon, facility_lat, facility_lon)

    if not enable_geocoding:
        return (fac_dist, "facility_coords")

    city_lat, city_lon = get_city_coordinates(city, country)

    if city_lat is None:
        return (fac_dist, "facility_coords")

    city_dist = hav(query_lat, query_lon, city_lat, city_lon)
    diff = abs(fac_dist - city_dist)

    if diff > threshold_km:
        print(f"  [Warning: {city}, {country} - facility coords ({fac_dist:.1f} km) "
              f"differ from city ({city_dist:.1f} km) by {diff:.1f} km. Using city fallback.]")
        return (city_dist, "city_fallback")

    return (fac_dist, "facility_coords")


def detect_facility_quality_issues(facility_data, distance_km, city, country):
    """
    Detect data quality issues in facility data.
    Returns list of flags (always returns a list, never None).
    """
    flags = []

    # Flag 1: Suspicious coordinates (far from city center)
    # Catches cases like "Cogent Fairfax" (listed as Fairfax but coords in SC)
    city_lat, city_lon = get_city_coordinates(city, country)
    if city_lat is not None:
        city_dist = hav(city_lat, city_lon, facility_data["latitude"], facility_data["longitude"])
        if city_dist > 100:  # >100km from city center is suspicious
            flags.append("coordinates_suspect")
            print(f"🚩 Quality flag: {facility_data.get('name')} has coordinates_suspect (>100km from {city})")

    # Flag 2: Multiple city names (distributed facility)
    if any(sep in city for sep in [',', ';', '/', '|']):
        flags.append("distributed_location")

    # Flag 3: Missing operator
    if not facility_data.get("org_name"):
        flags.append("missing_operator")

    return flags  # Always return list, never None


def detect_ixp_quality_issues(ix_data, distance_km, facility_count):
    """
    Detect data quality issues in IXP data.
    Returns list of flags (always returns a list, never None).
    """
    flags = []

    # Flag 1: Distributed IXP (multiple cities)
    city = ix_data.get("city", "")
    if any(sep in city for sep in [',', ';', '/', '|']):
        flags.append("distributed_ixp")

    # Flag 2: Multiple facilities (indicates distributed IXP)
    if facility_count > 5:
        flags.append("many_facilities")

    # Flag 3: Very distant IXP (>400km is unusual)
    if distance_km > 400:
        flags.append("distant_location")

    # Flag 4: Missing ASN count
    if ix_data.get("net_count") is None:
        flags.append("missing_asn_count")

    return flags  # Always return list, never None


# ----------------------------------------------------
# PeeringDB Query
# ----------------------------------------------------
def query_peeringdb(lat, lon, verbose=False):
    """
    Query PeeringDB for facilities, carriers, and IXPs near coordinates.

    Args:
        lat: Latitude
        lon: Longitude
        verbose: If True, print detailed progress and diagnostics
    """
    base = "https://peeringdb.com/api/"
    out_ixps = []
    out_fac = []
    carriers = set()
    last_updated = None

    def upd(ts):
        nonlocal last_updated
        if ts and (last_updated is None or ts > last_updated):
            last_updated = ts

    # ------------------------------------------------
    # 1) Facilities in bounding box
    # ------------------------------------------------
    q_fac = (
        f"{base}fac?"
        f"latitude__gte={lat-3}&latitude__lte={lat+3}&"
        f"longitude__gte={lon-3}&longitude__lte={lon+3}&"
        f"status=ok"
    )
    js = get_cached_or_fetch(q_fac)

    # Fallback: If bounding box query returns empty, try wider search
    if not js or not js.get("data"):
        print(f"  [Warning: No facilities found in ±3° box, trying ±5° fallback...]")
        q_fac_wide_fallback = (
            f"{base}fac?"
            f"latitude__gte={lat-5}&latitude__lte={lat+5}&"
            f"longitude__gte={lon-5}&longitude__lte={lon+5}&"
            f"status=ok"
        )
        js = get_cached_or_fetch(q_fac_wide_fallback)

    if verbose:
        result_count = len(js["data"]) if js and "data" in js else 0
        print(f"  Facilities query: {result_count} found")

    if js and "data" in js:
        for r in js["data"]:
            la = r.get("latitude")
            lo = r.get("longitude")
            city = r.get("city")
            country = r.get("country")

            # Exclude facilities without coordinates (per client requirement)
            if la is None or lo is None:
                continue

            # Calculate distance using facility coordinates
            dist = hav(lat, lon, la, lo)

            # Filter: only facilities within 200 km
            if dist > 200:
                continue

            out_fac.append({
                "name": r.get("name"),
                "operator": r.get("org_name"),
                "city": city,
                "country": country,
                "distance_km": round(dist, 2),
                "distance_method": "facility_coords",
                "data_quality_flag": detect_facility_quality_issues(r, dist, city, country),
                "id": r.get("id"),
            })

            upd(r.get("updated"))

    out_fac = sorted(out_fac, key=lambda x: x["distance_km"])[:5]
    fac_ids = [f["id"] for f in out_fac]

    if verbose:
        print(f"  Facilities within 200km: {len(out_fac)}")

    # ------------------------------------------------
    # 2) Get networks at these facilities via netfac
    # ------------------------------------------------
    if fac_ids:
        fac_id_str = ",".join(map(str, fac_ids))
        q_netfac = f"{base}netfac?fac_id__in={fac_id_str}"
        js = get_cached_or_fetch(q_netfac)

        if verbose:
            netfac_count = len(js["data"]) if js and "data" in js else 0
            print(f"  Network-facility relationships: {netfac_count}")

        if js and "data" in js:
            net_ids = list(set([nf.get("net_id") for nf in js["data"] if nf.get("net_id")]))

            if net_ids:
                net_id_str = ",".join(map(str, net_ids))
                q_net = f"{base}net?id__in={net_id_str}"
                js_net = get_cached_or_fetch(q_net)

                if js_net and "data" in js_net:
                    for net in js_net["data"]:
                        if net.get("name"):
                            carriers.add(normalize_carrier_name(net["name"]))

    # ------------------------------------------------
    # 3) Get IXPs within 500 km radius via facilities
    # ------------------------------------------------
    # Query all ixfac relationships within a wider radius to find nearby IXPs
    # Use ±5° lat/lon (~550 km) for facilities that might host IXPs
    q_fac_wide = (
        f"{base}fac?"
        f"latitude__gte={lat-5}&latitude__lte={lat+5}&"
        f"longitude__gte={lon-5}&longitude__lte={lon+5}&"
        f"status=ok"
    )
    js_fac_wide = get_cached_or_fetch(q_fac_wide)

    # Get local country from nearest facility for cross-border detection
    local_country = out_fac[0]["country"] if out_fac else None

    if js_fac_wide and "data" in js_fac_wide:
        # Build lookup of all facilities with coordinates in region
        wide_fac_lookup = {}
        wide_fac_ids = []
        for fac in js_fac_wide["data"]:
            if fac.get("latitude") is not None and fac.get("longitude") is not None:
                fac_id = fac["id"]
                dist = hav(lat, lon, fac["latitude"], fac["longitude"])
                # Only consider facilities within 500 km for IXP search
                if dist <= 500:
                    wide_fac_lookup[fac_id] = {
                        "lat": fac["latitude"],
                        "lon": fac["longitude"],
                        "distance_km": dist
                    }
                    wide_fac_ids.append(fac_id)

        # Process facilities in batches of 100 to avoid URL length issues
        if wide_fac_ids:
            batch_size = 100
            all_ixfac_data = []

            for i in range(0, len(wide_fac_ids), batch_size):
                batch_fac_ids = wide_fac_ids[i:i+batch_size]
                fac_id_batch_str = ",".join(map(str, batch_fac_ids))
                q_ixfac_batch = f"{base}ixfac?fac_id__in={fac_id_batch_str}"
                js_ixfac = get_cached_or_fetch(q_ixfac_batch)

                if js_ixfac and "data" in js_ixfac:
                    all_ixfac_data.extend(js_ixfac["data"])

            if all_ixfac_data:
                # Get unique IX IDs and query them in batches
                ix_ids = list(set([ixf["ix_id"] for ixf in all_ixfac_data if ixf.get("ix_id")]))

                # Query IXs in batches of 100
                all_ixs = []
                for i in range(0, len(ix_ids), batch_size):
                    batch_ix_ids = ix_ids[i:i+batch_size]
                    ix_id_batch_str = ",".join(map(str, batch_ix_ids))
                    q_ix_batch = f"{base}ix?id__in={ix_id_batch_str}"
                    js_ix = get_cached_or_fetch(q_ix_batch)

                    if js_ix and "data" in js_ix:
                        all_ixs.extend(js_ix["data"])

                if verbose:
                    print(f"  IXPs found: {len(all_ixs)}")

                # Process each IX
                for ix in all_ixs:
                    # Filter virtual IXPs with multiple cities
                    city = ix.get("city", "")
                    if any(sep in city for sep in [',', ';', '/', '|']):
                        continue

                    # Find closest facility for this IX
                    ix_fac_ids = [ixf["fac_id"] for ixf in all_ixfac_data
                                 if ixf.get("ix_id") == ix["id"] and ixf.get("fac_id") in wide_fac_lookup]

                    if not ix_fac_ids:
                        # No facilities found for this IX - skip it
                        continue

                    # Get minimum distance from any facility hosting this IX
                    min_dist = min(wide_fac_lookup[fac_id]["distance_km"] for fac_id in ix_fac_ids)
                    distance_method = "facility_coords"

                    # Determine IXP type - check country FIRST, then apply distance logic
                    ixp_type = "domestic"
                    if local_country and ix.get("country") != local_country:
                        # Different country = cross-border
                        if min_dist <= 500:
                            ixp_type = "regional_cross_border"
                        else:
                            ixp_type = "international"
                    # else: stays "domestic" (same country or unknown)

                    out_ixps.append({
                        "id": ix.get("id"),  # Store ID for deduplication
                        "name": ix.get("name"),
                        "city": ix.get("city"),
                        "country": ix.get("country"),
                        "distance_km": round(min_dist, 2),
                        "distance_method": distance_method,
                        "asn_count": ix.get("net_count"),
                        "ixp_type": ixp_type,
                        "data_quality_flag": detect_ixp_quality_issues(ix, min_dist, len(ix_fac_ids)),
                    })

                    upd(ix.get("updated"))

    out_ixps = sorted(out_ixps, key=lambda x: x["distance_km"])[:3]

    # NEW FALLBACK: Check if any facilities in top 5 host IXPs not yet found
    # This catches cases like Bridge IX Columbia at DartPoints Columbia
    # OPTIMIZED: Use batched query instead of per-facility queries to avoid rate limiting
    if out_fac:  # Only run if we have facilities
        # Track which IXP IDs we already have
        existing_ixp_ids = set()
        for ixp in out_ixps:
            if "id" in ixp:
                existing_ixp_ids.add(ixp["id"])

        # Collect facility IDs for batch query
        fallback_fac_ids = [fac.get("id") for fac in out_fac[:5] if fac.get("id")]

        if fallback_fac_ids:
            # Single batched query for all facility IXP relationships (suppress empty warnings)
            fac_id_str = ",".join(map(str, fallback_fac_ids))
            q_ixfac_batch = f"{base}ixfac?fac_id__in={fac_id_str}"
            js_ixfac_fb = get_cached_or_fetch(q_ixfac_batch, timeout=10, warn_on_empty=False)

            if js_ixfac_fb and "data" in js_ixfac_fb:
                # Build fac_id -> distance lookup
                fac_dist_lookup = {fac.get("id"): fac["distance_km"] for fac in out_fac[:5] if fac.get("id")}

                # Collect unique IX IDs we haven't seen yet
                new_ix_ids = set()
                ix_to_fac_dist = {}  # Track closest facility distance for each IX
                for ixfac in js_ixfac_fb["data"]:
                    ix_id = ixfac.get("ix_id")
                    fac_id = ixfac.get("fac_id")
                    if ix_id and ix_id not in existing_ixp_ids and fac_id in fac_dist_lookup:
                        new_ix_ids.add(ix_id)
                        # Track minimum distance
                        fac_dist = fac_dist_lookup[fac_id]
                        if ix_id not in ix_to_fac_dist or fac_dist < ix_to_fac_dist[ix_id]:
                            ix_to_fac_dist[ix_id] = fac_dist

                # Batch query for IX details
                if new_ix_ids:
                    ix_id_str = ",".join(map(str, new_ix_ids))
                    q_ix_batch = f"{base}ix?id__in={ix_id_str}"
                    js_ix = get_cached_or_fetch(q_ix_batch, timeout=10)

                    if js_ix and "data" in js_ix:
                        for ix in js_ix["data"]:
                            # Apply same filters as main IXP query
                            city = ix.get("city", "")
                            if any(sep in city for sep in [',', ';', '/', '|']):
                                continue  # Skip virtual IXPs

                            ix_id = ix["id"]
                            fac_dist = ix_to_fac_dist.get(ix_id, 0)

                            # Determine IXP type
                            ixp_type = "domestic"
                            if local_country and ix.get("country") != local_country:
                                if fac_dist <= 500:
                                    ixp_type = "regional_cross_border"
                                else:
                                    ixp_type = "international"

                            out_ixps.append({
                                "id": ix_id,
                                "name": ix.get("name", "Unknown IXP"),
                                "city": ix.get("city"),
                                "country": ix.get("country"),
                                "asn_count": ix.get("net_count"),
                                "distance_km": fac_dist,
                                "distance_method": "facility_coords",
                                "ixp_type": ixp_type,
                                "data_quality_flag": detect_ixp_quality_issues(ix, fac_dist, 1),
                            })
                            existing_ixp_ids.add(ix_id)
                            upd(ix.get("updated"))

        # Re-sort after fallback additions and take top 3
        out_ixps = sorted(out_ixps, key=lambda x: x["distance_km"])[:3]

        if verbose:
            print(f"  IXPs after facility-based fallback: {len(out_ixps)}")

    # Smart fallback: detect IXP operators in facilities and move them to IXPs
    # This handles cases where IXP query failed but facility with IXP operator shows up
    ix_operator_patterns = [
        r'\bIX\b', r'\bIXP\b', r'Internet Exchange', r'Peering',
        r'\bNAP\b', r'Network Access Point'
    ]

    remaining_fac = []
    for fac in out_fac:
        operator = fac.get("operator", "")
        # Check if operator name suggests this is an IXP
        is_ix_operator = any(re.search(pattern, operator, re.IGNORECASE)
                            for pattern in ix_operator_patterns)

        if is_ix_operator:
            # Move to IXPs array
            ixp_type = "domestic"
            if local_country and fac.get("country") != local_country:
                if fac["distance_km"] <= 500:
                    ixp_type = "regional_cross_border"
                else:
                    ixp_type = "international"

            out_ixps.append({
                "name": operator,  # Use operator name as IXP name
                "city": fac["city"],
                "country": fac["country"],
                "distance_km": fac["distance_km"],
                "distance_method": fac["distance_method"],
                "asn_count": None,  # Unknown from facility data
                "ixp_type": ixp_type,
                "data_quality_flag": fac.get("data_quality_flag"),  # Carry over from facility
            })
        else:
            remaining_fac.append(fac)

    out_fac = remaining_fac
    # Sort all IXPs and take top 3 (this allows facility-derived IXPs to compete with direct IXP query results)
    out_ixps = sorted(out_ixps, key=lambda x: x["distance_km"])[:3]

    if verbose:
        print(f"  IXPs after smart fallback: {len(out_ixps)}")

    # Final validation: ensure cross-border IXPs are never marked as domestic
    for ixp in out_ixps:
        if local_country and ixp.get("country") and ixp.get("country") != local_country:
            if ixp.get("ixp_type") == "domestic":
                # Fix incorrect classification
                if ixp["distance_km"] <= 500:
                    ixp["ixp_type"] = "regional_cross_border"
                else:
                    ixp["ixp_type"] = "international"

    # Clean up facilities and IXPs - remove internal IDs
    for fac in out_fac:
        fac.pop("id", None)
    for ixp in out_ixps:
        ixp.pop("id", None)

    return {
        "ixps": out_ixps,
        "facilities": out_fac,
        "carriers": sorted(list(carriers)),
        "last_updated": last_updated,
    }


# ----------------------------------------------------
# TEST ENTRYPOINT
# ----------------------------------------------------
if __name__ == "__main__":
    lat = 38.9072
    lon = -77.0369

    print("Querying PeeringDB...\n")
    data = query_peeringdb(lat, lon)

    print(json.dumps(data, indent=2))
