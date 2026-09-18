"""
Unit tests for solarscan.osm and solarscan.fixtures modules.
"""

import os
import pytest
from solarscan.osm import parse_google_maps_url
from solarscan.fixtures import load_fixture
from solarscan.geometry import latlon_to_meters, calculate_shoelace_area
from solarscan.cli import run_scan


def test_parse_google_maps_pin_url():
    """Extracts coordinates from Google Maps pinned URL."""
    url = "https://www.google.com/maps/place/CS+W5/@25.2893,55.4783,18z/data=!3d25.2893304!4d55.4783103"
    coords = parse_google_maps_url(url)
    assert coords is not None
    lat, lon = coords
    assert pytest.approx(lat, 1e-4) == 25.2893304
    assert pytest.approx(lon, 1e-4) == 55.4783103


def test_parse_google_maps_viewport_url():
    """Extracts coordinates from viewport URL."""
    url = "https://www.google.com/maps/@25.2893304,55.4783103,19z"
    coords = parse_google_maps_url(url)
    assert coords is not None
    lat, lon = coords
    assert pytest.approx(lat, 1e-4) == 25.2893304
    assert pytest.approx(lon, 1e-4) == 55.4783103


def test_parse_raw_coords_string():
    """Parses raw lat, lon comma-separated string."""
    text = "25.2893304, 55.4783103"
    coords = parse_google_maps_url(text)
    assert coords is not None
    lat, lon = coords
    assert pytest.approx(lat, 1e-4) == 25.2893304
    assert pytest.approx(lon, 1e-4) == 55.4783103


def test_load_w5_fixture():
    """Verifies that uos_w5 fixture loads properly and computes valid area."""
    fixture_file = os.path.join("data", "fixtures", "uos_w5.json")
    assert os.path.exists(fixture_file)
    data = load_fixture(fixture_file)
    assert data["building_id"] == 204709053
    assert len(data["polygon_coords"]) >= 10
    
    meters = latlon_to_meters(data["polygon_coords"])
    area = calculate_shoelace_area(meters)
    # W5 footprint area is approximately 1610 m2
    assert 1500.0 < area < 1700.0


def test_end_to_end_w5_scan(tmp_path):
    """Runs deterministic end-to-end scan on W5 fixture."""
    fixture_file = os.path.join("data", "fixtures", "uos_w5.json")
    out_dir = str(tmp_path / "reports")
    
    out_report = run_scan(
        address="Computer Science Department W5 Sharjah",
        fixture_path=fixture_file,
        tilt=15.0,
        rate_aed=0.38,
        out_dir=out_dir,
        fmt="both"
    )
    assert os.path.exists(out_report)
