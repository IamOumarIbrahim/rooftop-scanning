"""
Unit and integration tests for SolarScan CLI interface.
"""

import os
import pytest
from solarscan.cli import run_scan, load_config

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W5_FIXTURE = os.path.join(ROOT, "data", "fixtures", "uos_w5.json")


def test_load_config_defaults():
    cfg = load_config("non_existent_config.yaml")
    assert cfg["default_tilt_deg"] == 15.0
    assert cfg["module_efficiency"] == 0.20
    assert cfg["rate_aed"] == 0.38


def test_run_scan_with_fixture(tmp_path):
    out_dir = str(tmp_path / "reports")
    res = run_scan(
        address="Test University W5",
        fixture_path=W5_FIXTURE,
        out_dir=out_dir,
        fmt="both"
    )
    assert os.path.exists(res)
    assert os.path.exists(os.path.join(out_dir, "SolarScan_Report_Test_University_W5.pdf"))
    assert os.path.exists(os.path.join(out_dir, "SolarScan_Report_Test_University_W5.html"))


def test_run_scan_empty_address():
    with pytest.raises(ValueError, match="cannot be empty"):
        run_scan(address="   ")


def test_run_scan_mismatched_coordinates():
    with pytest.raises(ValueError, match="Both latitude and longitude"):
        run_scan(address="Test", lat=25.0, lon=None)

    with pytest.raises(ValueError, match="Both latitude and longitude"):
        run_scan(address="Test", lat=None, lon=55.0)


def test_run_scan_out_of_bounds_coordinates():
    with pytest.raises(ValueError, match="Latitude 105.0 is out of valid range"):
        run_scan(address="Test", lat=105.0, lon=55.0)

    with pytest.raises(ValueError, match="Longitude -190.0 is out of valid range"):
        run_scan(address="Test", lat=25.0, lon=-190.0)
