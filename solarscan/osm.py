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

    def _is_valid(lat: float, lon: float) -> bool:
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0

    # Priority 1: Exact Pinned Building Location (!3d<lat>!4d<lon>)
    match_pin = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', text)
    if match_pin:
        lat, lon = float(match_pin.group(1)), float(match_pin.group(2))
        if _is_valid(lat, lon):
            return lat, lon

    # Priority 2: Map Viewport / Camera Coordinates (@lat,lon)
    match_view = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if match_view:
        lat, lon = float(match_view.group(1)), float(match_view.group(2))
        if _is_valid(lat, lon):
            return lat, lon

    # Priority 3: Query parameters (q=lat,lon or ll=lat,lon)
    match_q = re.search(r'[?&](?:q|ll)=(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if match_q:
        lat, lon = float(match_q.group(1)), float(match_q.group(2))
        if _is_valid(lat, lon):
            return lat, lon

    # Priority 4: /place/lat,lon or /search/lat,lon
    match_p = re.search(r'/(?:place|search)/(-?\d+\.\d+)[,\+]+(-?\d+\.\d+)', text)
    if match_p:
        lat, lon = float(match_p.group(1)), float(match_p.group(2))
        if _is_valid(lat, lon):
            return lat, lon

    # Priority 5: Raw "lat, lon"
    match_raw = re.search(r'^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$', text)
    if match_raw:
        lat, lon = float(match_raw.group(1)), float(match_raw.group(2))
        if _is_valid(lat, lon):
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
        raise ConnectionError(f"Geocoding failed for '{address}': {e}") from e
    raise LookupError(f"Address not found: '{address}'. Pass --lat/--lon instead.")


def _contains(polygon_coords, lat: float, lon: float) -> bool:
    """Ray-casting point-in-polygon test in (lat, lon) space."""
    inside = False
    n = len(polygon_coords)
    for i in range(n):
        y1, x1 = polygon_coords[i]
        y2, x2 = polygon_coords[(i + 1) % n]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def query_osm_building(lat: float, lon: float, search_radius_m: int = 250) -> Dict[str, Any]:
    """
    Queries OpenStreetMap Overpass API for building footprint polygons near (lat, lon).
    Fails over across mirrors. Raises LookupError if no building is found and
    ConnectionError if every mirror fails. It never invents a polygon.
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
                last_exception = RuntimeError(f"HTTP {res.status_code} from {mirror_url}")
                continue
            
            data = res.json()
            elements = data.get("elements", [])
            nodes = {e["id"]: (e["lat"], e["lon"]) for e in elements if e.get("type") == "node"}
            ways = {e["id"]: e for e in elements if e.get("type") == "way" and "nodes" in e}
            relations = [e for e in elements if e.get("type") == "relation"]

            inner_way_ids = set()
            valid_candidates = []

            # 1. Process OSM Relations (Multipolygon buildings with courtyards/holes)
            for rel in relations:
                members = rel.get("members", [])
                rel_outer_ways = [m["ref"] for m in members if m.get("role") in ("outer", "") and m.get("type") == "way"]
                rel_inner_ways = [m["ref"] for m in members if m.get("role") == "inner" and m.get("type") == "way"]

                for i_wid in rel_inner_ways:
                    inner_way_ids.add(i_wid)

                rel_obstruction_area = 0.0
                for i_wid in rel_inner_ways:
                    if i_wid in ways:
                        inner_coords = [nodes[nid] for nid in ways[i_wid]["nodes"] if nid in nodes]
                        if len(inner_coords) >= 3:
                            inner_meters = latlon_to_meters(inner_coords)
                            rel_obstruction_area += calculate_shoelace_area(inner_meters)

                for o_wid in rel_outer_ways:
                    if o_wid in ways:
                        polygon_coords = [nodes[nid] for nid in ways[o_wid]["nodes"] if nid in nodes]
                        if len(polygon_coords) >= 3:
                            meter_coords = latlon_to_meters(polygon_coords)
                            area = calculate_shoelace_area(meter_coords)
                            cent_lat = sum(p[0] for p in polygon_coords) / len(polygon_coords)
                            cent_lon = sum(p[1] for p in polygon_coords) / len(polygon_coords)
                            dy = (cent_lat - lat) * 111000.0
                            dx = (cent_lon - lon) * 111000.0 * math.cos(math.radians(lat))
                            dist_m = math.hypot(dx, dy)
                            valid_candidates.append({
                                "building_id": rel.get("id", o_wid),
                                "polygon_coords": polygon_coords,
                                "area": area,
                                "dist_m": dist_m,
                                "obstruction_area": round(rel_obstruction_area, 2)
                            })

            # 2. Process Standalone Ways (excluding inner courtyards of relations)
            for wid, way in ways.items():
                if wid in inner_way_ids:
                    continue
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

            if not valid_candidates:
                last_exception = None  # the mirror answered: there is simply no building here
                break
            if valid_candidates:
                # A building that contains the query point always wins; otherwise the nearest centroid.
                for c in valid_candidates:
                    c["contains"] = _contains(c["polygon_coords"], lat, lon)
                valid_candidates.sort(key=lambda c: (not c["contains"], c["dist_m"]))
                selected = valid_candidates[0]
                logging.info(f"OSM building polygon retrieved: ID {selected['building_id']}, dist: {selected['dist_m']:.1f}m")
                return {
                    "building_id": selected["building_id"],
                    "polygon_coords": selected["polygon_coords"],
                    "obstruction_area": selected.get("obstruction_area", 0.0),
                    "query_lat": lat,
                    "query_lon": lon
                }
        except Exception as e:
            last_exception = e
            logging.warning(f"Mirror {mirror_url} failed: {e}")

    if last_exception is None:
        raise LookupError(f"No OSM building found within {search_radius_m} m of ({lat}, {lon}).")
    raise ConnectionError(f"All Overpass mirrors failed: {last_exception}")
