"""
Unit tests for solarscan.report module.
"""

import os
import pytest
from solarscan.report import (
    generate_footprint_diagram,
    generate_svg_footprint,
    generate_html_report,
    generate_pdf_report
)

SAMPLE_COORDS = [
    (0.0, 0.0),
    (30.0, 0.0),
    (30.0, 20.0),
    (0.0, 20.0)
]

SAMPLE_REPORT_DATA = {
    "address": "123 Solar Way, Sharjah <script>alert(1)</script>",
    "lat": 25.2893,
    "lon": 55.4783,
    "meter_coords": SAMPLE_COORDS,
    "raw_area": 600.0,
    "perimeter": 100.0,
    "usable_area": 450.0,
    "setback_m": 1.5,
    "module_efficiency": 0.20,
    "dc_capacity_kw": 90.0,
    "ac_capacity_kw": 75.0,
    "azimuth_deg": 90.0,
    "tilt_deg": 15.0,
    "annual_kwh": 140000.0,
    "rate_aed": 0.38,
    "payback_years": 2.85
}


def test_generate_footprint_diagram(tmp_path):
    png_path = str(tmp_path / "diag.png")
    generate_footprint_diagram(SAMPLE_COORDS, png_path)
    assert os.path.exists(png_path)
    assert os.path.getsize(png_path) > 1000


def test_generate_svg_footprint():
    svg = generate_svg_footprint(SAMPLE_COORDS)
    assert "<svg" in svg
    assert "<polygon" in svg
    assert "viewBox" in svg


def test_generate_html_report_escaping(tmp_path):
    html_path = str(tmp_path / "report.html")
    generate_html_report(SAMPLE_REPORT_DATA, html_path)
    assert os.path.exists(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Ensure XSS injection was escaped
    assert "<script>" not in content
    assert "&lt;script&gt;" in content
    assert "Avoided Carbon Emissions" in content
    assert "Specific Annual Yield" in content


def test_generate_pdf_report(tmp_path):
    pdf_path = str(tmp_path / "report.pdf")
    generate_pdf_report(SAMPLE_REPORT_DATA, pdf_path)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 10000
    # Ensure no leftover temporary PNGs
    temp_files = [f for f in os.listdir(tmp_path) if f.endswith(".png")]
    assert len(temp_files) == 0
