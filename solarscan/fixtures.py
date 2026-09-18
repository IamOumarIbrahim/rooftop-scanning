"""
Fixtures module for rooftop solar pre-feasibility analysis.
Provides deterministic loading and capturing of offline building polygon fixtures.
"""

import json
import os
from typing import Dict, Any, List, Tuple


def capture_fixture(lat: float, lon: float, out_path: str) -> Dict[str, Any]:
    """
    Queries OSM Overpass API for coordinates and saves building data as JSON fixture.
    """
    from solarscan.osm import query_osm_building
    result = query_osm_building(lat, lon)
    fixture_data = {
        "building_id": result["building_id"],
        "polygon_coords": result["polygon_coords"],
        "obstruction_area": result.get("obstruction_area", 0.0),
        "query_lat": lat,
        "query_lon": lon
    }
    
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixture_data, f, indent=2)
        
    return fixture_data


def load_fixture(path: str) -> Dict[str, Any]:
    """
    Loads an offline JSON fixture file and returns building polygon dictionary.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    polygon_coords = [tuple(pt) for pt in data["polygon_coords"]]
    return {
        "building_id": data["building_id"],
        "polygon_coords": polygon_coords,
        "obstruction_area": data.get("obstruction_area", 0.0),
        "query_lat": data.get("query_lat", polygon_coords[0][0] if polygon_coords else 0.0),
        "query_lon": data.get("query_lon", polygon_coords[0][1] if polygon_coords else 0.0)
    }
