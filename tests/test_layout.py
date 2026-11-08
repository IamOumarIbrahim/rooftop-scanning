"""Tests for solarscan.layout (module-by-module row layout)."""
import math

from shapely import affinity
from shapely.geometry import Polygon, box

from solarscan.layout import layout_modules, packing_estimate


def test_rectangle_closed_form():
    # 20 m (E-W) x 10 m (N-S). Footprint depth 2*cos15 = 1.932 m, pitch 2/0.7 = 2.857 m.
    # Rows that fit: floor((10 - 1.932) / 2.857) + 1 = 3; modules per row: 20. Total 60.
    roof = box(0, 0, 20, 10)
    out = layout_modules(roof, 1.0, 2.0, 15.0, 0.70)
    assert out["n"] == 60
    assert math.isclose(out["pitch_m"], 2 / 0.7) and math.isclose(out["depth_m"], 2 * math.cos(math.radians(15)))


def test_modules_inside_roof_and_not_overlapping():
    roof = Polygon([(0, 0), (30, 5), (25, 28), (3, 22)])
    out = layout_modules(roof)
    rects = [Polygon(m) for m in out["modules"]]
    assert out["n"] > 0
    assert all(roof.buffer(1e-6).contains(r) for r in rects)
    assert all(rects[i].intersection(rects[j]).area < 1e-9 for i in range(len(rects)) for j in range(i + 1, min(len(rects), i + 40)))


def test_rectangles_match_closed_form():
    # For an axis-aligned W x H roof: rows = floor((H - depth) / pitch) + 1, modules per row = floor(W / 1 m).
    # The last row needs only its depth, not a full pitch, so this can exceed the packing rule slightly.
    depth, pitch = 2 * math.cos(math.radians(15)), 2 / 0.7
    for w, h in ((40, 25), (13, 7), (55, 18)):
        expected = (math.floor((h - depth) / pitch) + 1) * w
        assert layout_modules(box(0, 0, w, h))["n"] == expected
    assert layout_modules(box(0, 0, 40, 25))["n"] > packing_estimate(1000)


def test_facing_direction_rotates_rows():
    roof = box(0, 0, 30, 12)
    south = layout_modules(roof, azimuth_deg=180)
    east = layout_modules(affinity.rotate(roof, 90, origin="centroid"), azimuth_deg=90)
    assert abs(south["n"] - east["n"]) <= 2  # same roof turned by 90 deg with rows turned too


def test_empty_roof():
    assert layout_modules(Polygon())["n"] == 0
