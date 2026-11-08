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
    assert "System assumed" in content and "Limits" in content and "crystalline Si" in content
    assert "OpenStreetMap contributors" in content  # ODbL attribution is required


def test_generate_pdf_report(tmp_path):
    pdf_path = str(tmp_path / "report.pdf")
    generate_pdf_report(SAMPLE_REPORT_DATA, pdf_path)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 10000
    # Ensure no leftover temporary PNGs
    temp_files = [f for f in os.listdir(tmp_path) if f.endswith(".png")]
    assert len(temp_files) == 0


def test_report_content_payback_grid_is_centered_and_closed_form():
    from solarscan.report import build_report_content
    d = dict(SAMPLE_REPORT_DATA, cost_per_kw=3000.0, rate_aed=0.38, n_modules=225)
    c = build_report_content(d)
    sy = d["annual_kwh"] / d["dc_capacity_kw"]
    i, j = c["base"]
    assert c["costs"][i] == 3000.0 and c["tariffs"][j] == 0.38
    assert abs(c["grid"][i][j] - 3000.0 / (sy * 0.38)) < 1e-3  # yield is rounded to 0.01 kWh/kWp
    assert c["grid"][0][-1] < c["grid"][i][j] < c["grid"][-1][0]  # cheaper + pricier power -> shorter payback
    assert any("OpenStreetMap" in b for _, b in c["limits"])
    # the roof-use bar adds up to the footprint area
    assert abs(sum(a for _, a, _ in c["roof_use"]) - d["raw_area"]) < 1e-6
