"""
Unit tests for solarscan.osm and solarscan.fixtures modules.
"""

import os
import pytest
import requests
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


def test_capture_fixture(monkeypatch, tmp_path):
    from solarscan import fixtures
    mock_result = {
        "building_id": 123456,
        "polygon_coords": [(25.0, 55.0), (25.01, 55.0), (25.01, 55.01), (25.0, 55.0)],
        "obstruction_area": 12.5
    }
    monkeypatch.setattr("solarscan.osm.query_osm_building", lambda lat, lon: mock_result)
    out_json = str(tmp_path / "mock_fixture.json")
    saved = fixtures.capture_fixture(25.0, 55.0, out_json)
    assert saved["building_id"] == 123456
    assert os.path.exists(out_json)
    loaded = fixtures.load_fixture(out_json)
    assert loaded["building_id"] == 123456
    assert loaded["obstruction_area"] == 12.5


def test_query_osm_building_with_courtyard_relation(monkeypatch):
    """Verifies that OSM relations with inner courtyards are properly parsed and inner rings are not selected as buildings."""
    import requests
    from solarscan.osm import query_osm_building

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "elements": [
                    {"type": "node", "id": 1, "lat": 25.000, "lon": 55.000},
                    {"type": "node", "id": 2, "lat": 25.000, "lon": 55.004},
                    {"type": "node", "id": 3, "lat": 25.004, "lon": 55.004},
                    {"type": "node", "id": 4, "lat": 25.004, "lon": 55.000},
                    {"type": "node", "id": 5, "lat": 25.001, "lon": 55.001},
                    {"type": "node", "id": 6, "lat": 25.001, "lon": 55.002},
                    {"type": "node", "id": 7, "lat": 25.002, "lon": 55.002},
                    {"type": "node", "id": 8, "lat": 25.002, "lon": 55.001},
                    {"type": "way", "id": 101, "nodes": [1, 2, 3, 4, 1]},
                    {"type": "way", "id": 102, "nodes": [5, 6, 7, 8, 5]},
                    {
                        "type": "relation",
                        "id": 99999,
                        "tags": {"building": "university", "type": "multipolygon"},
                        "members": [
                            {"type": "way", "ref": 101, "role": "outer"},
                            {"type": "way", "ref": 102, "role": "inner"}
                        ]
                    }
                ]
            }

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: MockResponse())
    result = query_osm_building(lat=25.0015, lon=55.0015)
    # The building selected must be the relation (or outer way 101), NOT inner courtyard way 102
    assert result["building_id"] in (99999, 101)
    assert result["building_id"] != 102
    # The inner courtyard must be recorded as non-zero obstruction area
    assert result["obstruction_area"] > 5000.0
    # Outer polygon coords must have 5 vertices
    assert len(result["polygon_coords"]) == 5




class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError(str(self.status_code))


def _square(node0, way_id, lat, lon, d):
    nodes = [{"type": "node", "id": node0 + i, "lat": lat + dy, "lon": lon + dx}
             for i, (dy, dx) in enumerate([(-d, -d), (-d, d), (d, d), (d, -d)])]
    way = {"type": "way", "id": way_id, "nodes": [n["id"] for n in nodes] + [node0], "tags": {"building": "yes"}}
    return nodes + [way]


def test_no_building_raises_instead_of_inventing_one(monkeypatch):
    """The old code returned a synthetic 33 m square. Now it must fail loudly."""
    from solarscan.osm import query_osm_building
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp({"elements": []}))
    with pytest.raises(LookupError):
        query_osm_building(25.0, 55.0)


def test_network_failure_raises(monkeypatch):
    from solarscan.osm import query_osm_building

    def boom(*a, **k):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(ConnectionError):
        query_osm_building(25.0, 55.0)


def test_geocode_failure_raises(monkeypatch):
    """The old code silently returned University of Sharjah coordinates."""
    from solarscan.osm import geocode_address
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp([]))
    with pytest.raises(LookupError):
        geocode_address("Nowhere Street 999")


def test_containing_building_wins_over_nearer_centroid(monkeypatch):
    """A big building that contains the point must win over a small one whose centre is closer."""
    from solarscan.osm import query_osm_building
    lat, lon = 25.0, 55.0
    big = _square(1, 100, lat + 0.0004, lon, 0.0006)        # contains the point, centre 44 m away
    small = _square(10, 200, lat - 0.00025, lon, 0.00005)   # outside, centre 28 m away
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp({"elements": big + small}))
    assert query_osm_building(lat, lon)["building_id"] == 100
