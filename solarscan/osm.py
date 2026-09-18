"""
OpenStreetMap (OSM) interface module.
Handles geocoding, Google Maps URL coordinate extraction, and Overpass API queries.
"""

import math
import requests
import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from solarscan.geometry import latlon_to_meters, calculate_shoelace_area

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

DEFAULT_HEADERS = {
    "User-Agent": "SolarScan/0.2.0 (Open Rooftop PV Pre-Feasibility Research Framework; contact@research.org)"
}


def parse_google_maps_url(text: str) -> Optional[Tuple[float, float]]:
    """
    Extracts (lat, lon) from Google Maps URLs, shortened links, or coordinate strings.
    Prioritizes exact building pin coordinates (!3d<lat>!4d<lon>) when present.
    """
    if not text:
        return None
        
    text = text.strip()
    if "maps.app.goo.gl" in text or "goo.gl/maps" in text:
        try:
            r = requests.head(text, allow_redirects=True, timeout=5, headers=DEFAULT_HEADERS)
            if r.url:
                text = r.url
        except Exception:
            pass

    # Priority 1: Exact Pinned Building Location (!3d<lat>!4d<lon>)
    match_pin = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', text)
    if match_pin:
        return float(match_pin.group(1)), float(match_pin.group(2))

    # Priority 2: Map Viewport / Camera Coordinates (@lat,lon)
    match_view = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if match_view:
        return float(match_view.group(1)), float(match_view.group(2))

    # Priority 3: Query parameters (q=lat,lon or ll=lat,lon)
    match_q = re.search(r'[?&](?:q|ll)=(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if match_q:
        return float(match_q.group(1)), float(match_q.group(2))

    # Priority 4: /place/lat,lon or /search/lat,lon
    match_p = re.search(r'/(?:place|search)/(-?\d+\.\d+)[,\+]+(-?\d+\.\d+)', text)
    if match_p:
        return float(match_p.group(1)), float(match_p.group(2))

    # Priority 5: Raw "lat, lon"
    match_raw = re.search(r'^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$', text)
    if match_raw:
        lat, lon = float(match_raw.group(1)), float(match_raw.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            return lat, lon

    return None


def geocode_address(address: str) -> Tuple[float, float]:
    """
    Geocodes an address string or Google Maps URL into (lat, lon).
    Auto-detects Google Maps URLs or raw GPS coordinates before calling Nominatim.
    """
    parsed_gmaps = parse_google_maps_url(address)
    if parsed_gmaps:
        logging.info(f"Parsed coordinates from input: {parsed_gmaps}")
        return parsed_gmaps

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    
    try:
        res = requests.get(url, headers=DEFAULT_HEADERS, params=params, timeout=6.0)
        res.raise_for_status()
        data = res.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logging.warning(f"Geocoding query failed for '{address}': {e}")
        
    # Regional fallback coordinate: University of Sharjah, UAE
    return 25.2893304, 55.4783103


def query_osm_building(lat: float, lon: float, search_radius_m: int = 250) -> Dict[str, Any]:
    """
    Queries OpenStreetMap Overpass API for building footprint polygons near (lat, lon).
    Failovers across mirrors. If no building polygon is found or network fails,
    returns a synthetic square polygon for testing/offline continuity.
    """
    if search_radius_m <= 0:
        raise ValueError(f"Search radius must be positive, got {search_radius_m}")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} is out of bounds [-90, 90]")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} is out of bounds [-180, 180]")

    query = f"""
    [out:json][timeout:10];
    (
      way["building"](around:{search_radius_m},{lat},{lon});
      relation["building"](around:{search_radius_m},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """
    
    last_exception = None

    for mirror_url in OVERPASS_MIRRORS:
        try:
            res = requests.post(mirror_url, data={"data": query}, headers=DEFAULT_HEADERS, timeout=8.0)
            if res.status_code != 200:
                continue
            
            data = res.json()
            elements = data.get("elements", [])
            nodes = {e["id"]: (e["lat"], e["lon"]) for e in elements if e.get("type") == "node"}
            ways = [e for e in elements if e.get("type") == "way" and "nodes" in e]
            
            valid_candidates = []
            for way in ways:
                polygon_coords = [nodes[nid] for nid in way["nodes"] if nid in nodes]
                if len(polygon_coords) >= 3:
                    meter_coords = latlon_to_meters(polygon_coords)
                    area = calculate_shoelace_area(meter_coords)
                    cent_lat = sum(p[0] for p in polygon_coords) / len(polygon_coords)
                    cent_lon = sum(p[1] for p in polygon_coords) / len(polygon_coords)
                    dy = (cent_lat - lat) * 111000.0
                    dx = (cent_lon - lon) * 111000.0 * math.cos(math.radians(lat))
                    dist_m = math.hypot(dx, dy)
                    valid_candidates.append({
                        "building_id": way["id"],
                        "polygon_coords": polygon_coords,
                        "area": area,
                        "dist_m": dist_m,
                        "obstruction_area": 0.0
                    })

            if valid_candidates:
                valid_candidates.sort(key=lambda c: c["dist_m"])
                selected = valid_candidates[0]
                logging.info(f"OSM building polygon retrieved: ID {selected['building_id']}, dist: {selected['dist_m']:.1f}m")
                return {
                    "building_id": selected["building_id"],
                    "polygon_coords": selected["polygon_coords"],
                    "obstruction_area": 0.0,
                    "query_lat": lat,
                    "query_lon": lon
                }
        except Exception as e:
            last_exception = e
            logging.warning(f"Mirror {mirror_url} failed: {e}")

    logging.error(f"Overpass mirrors failed: {last_exception}. Using synthetic fallback.")
    
    # Fallback bounding box for offline continuity
    lat_delta = 0.00015
    lon_delta = 0.00015
    synthetic_polygon = [
        (lat - lat_delta, lon - lon_delta),
        (lat - lat_delta, lon + lon_delta),
        (lat + lat_delta, lon + lon_delta),
        (lat + lat_delta, lon - lon_delta),
    ]
    return {
        "building_id": "synthetic_fallback",
        "polygon_coords": synthetic_polygon,
        "obstruction_area": 0.0,
        "query_lat": lat,
        "query_lon": lon
    }
