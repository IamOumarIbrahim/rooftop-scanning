"""
Unit tests for solarscan.geometry module.
"""

import pytest
import math
from solarscan.geometry import (
    calculate_shoelace_area,
    calculate_perimeter,
    calculate_usable_area,
    calculate_dominant_azimuth,
    latlon_to_meters,
    calculate_usable_area_buffered,
    sanitize_polygon,
    calculate_polygon_centroid,
    calculate_bounding_box,
    calculate_aspect_ratio
)


def test_shoelace_rectangle():
    """Verifies shoelace area on a standard 10m x 20m rectangle."""
    vertices = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    area = calculate_shoelace_area(vertices)
    assert math.isclose(area, 200.0, rel_tol=1e-5)


def test_shoelace_triangle():
    """Verifies shoelace area on a right triangle."""
    vertices = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
    area = calculate_shoelace_area(vertices)
    assert math.isclose(area, 50.0, rel_tol=1e-5)


def test_perimeter_rectangle():
    """Verifies perimeter calculation on a 10m x 20m rectangle."""
    vertices = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    p = calculate_perimeter(vertices)
    assert math.isclose(p, 60.0, rel_tol=1e-5)


def test_usable_area_formula():
    """
    Verifies setback and obstruction subtraction:
    Raw = 200 m2, P = 60 m, setback = 1.5 m, obstruction = 10 m2.
    Usable = 200 - (60 * 1.5) - 10 = 100 m2.
    """
    usable = calculate_usable_area(200.0, 60.0, 1.5, 10.0)
    assert math.isclose(usable, 100.0, rel_tol=1e-5)


def test_usable_area_non_negative():
    """Ensures usable area clamps to zero when setback exceeds roof area."""
    usable = calculate_usable_area(100.0, 50.0, 3.0, 0.0)
    assert usable == 0.0


def test_dominant_azimuth():
    """
    Verifies dominant azimuth:
    Longest edge along X axis (East-West) -> dy=0, dx=30 -> 90 degrees (East).
    """
    vertices = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (0.0, 10.0)]
    azimuth = calculate_dominant_azimuth(vertices)
    assert math.isclose(azimuth, 90.0, abs_tol=1.0)


def test_latlon_to_meters():
    """Verifies that latlon_to_meters converts degrees to plausible metric scale."""
    coords = [
        (25.0000, 55.0000),
        (25.0010, 55.0000),
        (25.0010, 55.0010),
        (25.0000, 55.0010)
    ]
    meters = latlon_to_meters(coords)
    assert len(meters) == 4
    # 0.0010 degrees latitude is approx 111.19 meters
    dy = abs(meters[1][1] - meters[0][1])
    assert 100.0 < dy < 120.0


def test_buffered_usable_area():
    """Verifies that interior buffering reduces area proportionally."""
    vertices = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    buffered_usable = calculate_usable_area_buffered(vertices, setback_m=1.0)
    # Exact buffered rectangle of (20-2) x (10-2) = 18 x 8 = 144 m2
    assert 130.0 <= buffered_usable <= 150.0


def test_sanitize_polygon_closing_duplicate():
    coords = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
    cleaned = sanitize_polygon(coords)
    assert len(cleaned) == 4
    assert cleaned == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


def test_sanitize_polygon_consecutive_duplicates():
    coords = [(0.0, 0.0), (0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    cleaned = sanitize_polygon(coords)
    assert len(cleaned) == 4


def test_sanitize_polygon_non_finite():
    with pytest.raises(ValueError, match="Non-finite coordinate"):
        sanitize_polygon([(0.0, 0.0), (float('nan'), 1.0), (1.0, 1.0)])


def test_polygon_centroid():
    vertices = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    cx, cy = calculate_polygon_centroid(vertices)
    assert math.isclose(cx, 10.0, abs_tol=1e-3)
    assert math.isclose(cy, 5.0, abs_tol=1e-3)


def test_bounding_box_and_aspect_ratio():
    vertices = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]
    bbox = calculate_bounding_box(vertices)
    assert bbox == (0.0, 0.0, 40.0, 20.0)
    aspect = calculate_aspect_ratio(vertices)
    assert math.isclose(aspect, 2.0, abs_tol=1e-3)


def test_usable_area_negative_setback():
    usable = calculate_usable_area(100.0, 40.0, -1.5, -5.0)
    assert math.isclose(usable, 100.0, abs_tol=1e-5)

