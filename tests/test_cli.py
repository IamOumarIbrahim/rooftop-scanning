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


def test_run_scan_with_emirate_profile(tmp_path):
    out_dir = str(tmp_path / "reports_ad")
    res = run_scan(
        address="Abu Dhabi Solar Facility",
        fixture_path=W5_FIXTURE,
        out_dir=out_dir,
        emirate="abu_dhabi",
        fmt="pdf"
    )
    assert os.path.exists(res)


def test_cli_main_demo(monkeypatch, tmp_path):
    import sys
    from solarscan.cli import main
    monkeypatch.setattr(sys, "argv", ["solarscan", "demo", "--format", "html"])
    monkeypatch.setattr("solarscan.cli.run_scan", lambda *args, **kwargs: "mock_demo_report.html")
    main()


def test_cli_main_scan_with_emirate_tariff(monkeypatch, tmp_path):
    """Verifies that CLI main with --emirate uses regional tariff rather than being overridden."""
    import sys
    from solarscan.cli import main
    out_dir = str(tmp_path / "reports_cli_ad")
    captured_args = {}
    def mock_run_scan(*args, **kwargs):
        captured_args.update(kwargs)
        return "mock_report.pdf"
    
    monkeypatch.setattr("solarscan.cli.run_scan", mock_run_scan)
    monkeypatch.setattr(sys, "argv", [
        "solarscan", "scan", "AD Terminal",
        "--fixture", W5_FIXTURE,
        "--emirate", "abu_dhabi",
        "--out", out_dir
    ])
    main()
    assert captured_args["emirate"] == "abu_dhabi"
    assert captured_args["rate_aed"] is None  # Defaults to None so emirate profile is respected


def test_cli_batch_scan(tmp_path):
    from solarscan.cli import run_batch_scan
    csv_file = tmp_path / "batch.csv"
    csv_file.write_text(
        "address,lat,lon,emirate,fixture\n"
        f"Facility A,25.2893,55.4783,sharjah,{W5_FIXTURE}\n"
        f"Facility B,24.4539,54.3773,abu_dhabi,{W5_FIXTURE}\n",
        encoding="utf-8"
    )
    out_dir = str(tmp_path / "batch_reports")
    reports = run_batch_scan(str(csv_file), out_dir=out_dir, fmt="html")
    assert len(reports) == 2
    for r in reports:
        assert os.path.exists(r)


def test_cli_batch_scan_malformed_rows(tmp_path):
    from solarscan.cli import run_batch_scan
    csv_file = tmp_path / "bad_batch.csv"
    csv_file.write_text(
        "address,lat,lon,emirate,fixture\n"
        f"Valid Facility,25.2893,55.4783,sharjah,{W5_FIXTURE}\n"
        "Malformed Facility,invalid_lat,invalid_lon,sharjah,\n"
        "   ,25.0,55.0,sharjah,\n",
        encoding="utf-8"
    )
    out_dir = str(tmp_path / "bad_batch_reports")
    reports = run_batch_scan(str(csv_file), out_dir=out_dir, fmt="pdf")
    # Should successfully process the valid row and not crash on malformed rows
    assert len(reports) >= 1
    assert os.path.exists(reports[0])


def test_cli_batch_missing_file():
    from solarscan.cli import run_batch_scan
    with pytest.raises(FileNotFoundError, match="Batch CSV '.*' not found"):
        run_batch_scan("non_existent_batch.csv")


