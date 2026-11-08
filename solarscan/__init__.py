"""
SolarScan: rooftop PV pre-feasibility screening from OpenStreetMap building footprints.

Pipeline: address or coordinates -> OSM footprint -> metric projection -> area and
usable area -> array sizing -> PVGIS-based yield -> simple economics.
"""

from solarscan.geometry import (
    latlon_to_meters, calculate_shoelace_area, calculate_perimeter,
    calculate_usable_area, calculate_usable_area_buffered,
    calculate_building_axis, array_azimuth_aligned, calculate_dominant_azimuth,
    sanitize_polygon, calculate_polygon_centroid,
)
from solarscan.sizing import (
    calculate_dc_capacity, recommend_inverter_capacity, calculate_module_count, is_viable_system,
)
from solarscan.yield_estimate import (
    specific_yield, optimal_specific_yield, nearest_site, calculate_orientation_derate,
    estimate_annual_yield, estimate_simple_payback, calculate_lcoe, calculate_npv,
    calculate_discounted_payback, calculate_carbon_offset, calculate_specific_yield,
)
from solarscan.osm import parse_google_maps_url, geocode_address, query_osm_building
from solarscan.fixtures import load_fixture, capture_fixture
from solarscan.cli import run_scan, run_batch_scan
from solarscan.config import load_config, get_emirate_profile

__version__ = "1.0.0"

__all__ = [
    "latlon_to_meters", "calculate_shoelace_area", "calculate_perimeter",
    "calculate_usable_area", "calculate_usable_area_buffered",
    "calculate_building_axis", "array_azimuth_aligned", "calculate_dominant_azimuth",
    "sanitize_polygon", "calculate_polygon_centroid",
    "calculate_dc_capacity", "recommend_inverter_capacity", "calculate_module_count", "is_viable_system",
    "specific_yield", "optimal_specific_yield", "nearest_site", "calculate_orientation_derate",
    "estimate_annual_yield", "estimate_simple_payback", "calculate_lcoe", "calculate_npv",
    "calculate_discounted_payback", "calculate_carbon_offset", "calculate_specific_yield",
    "parse_google_maps_url", "geocode_address", "query_osm_building",
    "load_fixture", "capture_fixture", "run_scan", "run_batch_scan",
    "load_config", "get_emirate_profile",
]
