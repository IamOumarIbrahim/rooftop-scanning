"""
Unit tests for solarscan.geometry module.
"""

import pytest
import math
from solarscan.geometry import (
    calculate_building_axis,
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


def test_building_axis_and_array_azimuth():
    """A 30 m x 10 m box with its long side East-West has axis 90 deg; rows then face South."""
    box = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (0.0, 10.0)]
    assert math.isclose(calculate_building_axis(box), 90.0, abs_tol=0.5)
    assert math.isclose(calculate_dominant_azimuth(box), 180.0, abs_tol=0.5)


def test_azimuth_does_not_depend_on_vertex_order():
    """The old code returned 303.78 or 123.78 deg for the same W5 roof depending on vertex order."""
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "uos_w5.json")
    m = latlon_to_meters(json.load(open(path))["polygon_coords"])
    assert calculate_building_axis(m) == calculate_building_axis(m[::-1])
    assert calculate_dominant_azimuth(m) == calculate_dominant_azimuth(m[::-1])
    assert abs(calculate_dominant_azimuth(m) - 180.0) <= 45.0


def test_rotated_box_axis():
    """Rotate the box by 30 deg clockwise: axis 120 deg (mod 180), rows face 210 deg."""
    a = math.radians(30)
    box = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (0.0, 10.0)]
    rot = [(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)) for x, y in box]
    assert math.isclose(calculate_building_axis(rot), 120.0, abs_tol=0.5)
    assert math.isclose(calculate_dominant_azimuth(rot), 210.0, abs_tol=0.5)


def test_projection_matches_geodesic_area():
    """Local ellipsoidal projection agrees with pyproj geodesic area to < 0.01 %."""
    pyproj = pytest.importorskip("pyproj")
    import json, os, glob
    g = pyproj.Geod(ellps="WGS84")
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "*.json")):
        c = json.load(open(f))["polygon_coords"]
        ref = abs(g.polygon_area_perimeter([p[1] for p in c], [p[0] for p in c])[0])
        if ref > 0:
            assert abs(calculate_shoelace_area(latlon_to_meters(c)) - ref) / ref < 1e-4


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


def test_buffered_usable_area_with_holes():
    """Verifies that interior holes/courtyards reduce buffered usable area."""
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (0.0, 30.0)]
    inner_hole = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]
    without_hole = calculate_usable_area_buffered(outer, setback_m=1.0)
    with_hole = calculate_usable_area_buffered(outer, setback_m=1.0, holes=[inner_hole])
    # Total outer buffered: (40-2)*(30-2) = 38*28 = 1064 m2
    # Inner hole expands outward by 1m: (10+2)*(10+2) = 144 m2
    # Net with hole should be approx 1064 - 144 = 920 m2
    assert with_hole < without_hole
    assert 850.0 <= with_hole <= 950.0


def test_shoelace_non_finite_raises():
    """Verifies that calculate_shoelace_area and calculate_perimeter reject NaN coordinates."""
    bad_coords = [(0.0, 0.0), (float('nan'), 1.0), (1.0, 1.0)]
    with pytest.raises(ValueError, match="Non-finite coordinate"):
        calculate_shoelace_area(bad_coords)
    with pytest.raises(ValueError, match="Non-finite coordinate"):
        calculate_perimeter(bad_coords)


