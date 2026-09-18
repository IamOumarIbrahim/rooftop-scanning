"""
SolarScan: Open-source rooftop solar photovoltaic pre-feasibility framework.
Extracts building footprints from OpenStreetMap Overpass API and computes
footprint geometry, usable area, array sizing, and estimated energy yield.
"""

from solarscan.geometry import (
    latlon_to_meters, calculate_shoelace_area, calculate_perimeter,
    calculate_usable_area, calculate_dominant_azimuth, sanitize_polygon
)
from solarscan.sizing import (
    calculate_dc_capacity, recommend_inverter_capacity,
    calculate_module_count, is_viable_system
)
from solarscan.yield_estimate import (
    calculate_orientation_derate, estimate_annual_yield,
    estimate_simple_payback, calculate_lcoe, calculate_npv,
    calculate_discounted_payback, calculate_carbon_offset
)
from solarscan.config import load_config, get_emirate_profile

__version__ = "0.2.0"
__author__ = "Research Team"

__all__ = [
    "latlon_to_meters",
    "calculate_shoelace_area",
    "calculate_perimeter",
    "calculate_usable_area",
    "calculate_dominant_azimuth",
    "sanitize_polygon",
    "calculate_dc_capacity",
    "recommend_inverter_capacity",
    "calculate_module_count",
    "is_viable_system",
    "calculate_orientation_derate",
    "estimate_annual_yield",
    "estimate_simple_payback",
    "calculate_lcoe",
    "calculate_npv",
    "calculate_discounted_payback",
    "calculate_carbon_offset",
    "load_config",
    "get_emirate_profile",
]
