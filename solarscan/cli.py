"""
Command line interface (CLI) for SolarScan rooftop pre-feasibility framework.
"""

import argparse
import os
import sys
import yaml
import csv
import re
from typing import Dict, Any, Optional

from solarscan.osm import geocode_address, query_osm_building
from solarscan.fixtures import load_fixture
from solarscan.geometry import (
    latlon_to_meters, calculate_shoelace_area, calculate_perimeter,
    calculate_usable_area, calculate_dominant_azimuth
)
from solarscan.sizing import calculate_dc_capacity, recommend_inverter_capacity
from solarscan.yield_estimate import estimate_annual_yield, estimate_simple_payback
from solarscan.report import generate_pdf_report, generate_html_report


def load_config(config_path: str = "solarscan.yaml") -> Dict[str, Any]:
    """Loads default sizing and economic configuration."""
    defaults = {
        "default_tilt_deg": 15.0,
        "setback_m": 1.5,
        "module_efficiency": 0.20,
        "dc_ac_ratio": 1.2,
        "peak_sun_hours_per_day": 5.5,
        "system_loss_factor": 0.85,
        "cost_per_kw": 1000.0,
        "rate_aed": 0.38
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_cfg = yaml.safe_load(f)
                if isinstance(user_cfg, dict):
                    defaults.update(user_cfg)
        except Exception as e:
            print(f"Warning: Failed to load config {config_path}: {e}")
    return defaults


def run_scan(
    address: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    tilt: Optional[float] = None,
    rate_aed: Optional[float] = None,
    module_eff: Optional[float] = None,
    setback: Optional[float] = None,
    out_dir: str = "reports",
    config_path: str = "solarscan.yaml",
    fixture_path: Optional[str] = None,
    fmt: str = "pdf"
) -> str:
    """Executes end-to-end solar pre-feasibility screening."""
    cfg = load_config(config_path)
    
    tilt_deg = tilt if tilt is not None else cfg.get("default_tilt_deg", 15.0)
    setback_m = setback if setback is not None else cfg.get("setback_m", 1.5)
    eff = module_eff if module_eff is not None else cfg.get("module_efficiency", 0.20)
    dc_ac_ratio = cfg.get("dc_ac_ratio", 1.2)
    psh = cfg.get("peak_sun_hours_per_day", 5.5)
    sys_loss = cfg.get("system_loss_factor", 0.85)
    tariff = rate_aed if rate_aed is not None else cfg.get("rate_aed", 0.38)
    cost_per_kw = cfg.get("cost_per_kw", 1000.0)

    if not address or not address.strip():
        raise ValueError("Address or location query string cannot be empty.")

    if (lat is not None and lon is None) or (lon is not None and lat is None):
        raise ValueError("Both latitude and longitude must be provided together.")

    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} is out of valid range [-90, 90].")

    if lon is not None and not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} is out of valid range [-180, 180].")

    os.makedirs(out_dir, exist_ok=True)

    if fixture_path and os.path.exists(fixture_path):
        osm_data = load_fixture(fixture_path)
        lat = osm_data["query_lat"]
        lon = osm_data["query_lon"]
    else:
        if lat is None or lon is None:
            lat, lon = geocode_address(address)
        osm_data = query_osm_building(lat, lon)

    polygon_coords = osm_data["polygon_coords"]
    obstruction_area = osm_data.get("obstruction_area", 0.0)

    meter_coords = latlon_to_meters(polygon_coords)
    raw_area = calculate_shoelace_area(meter_coords)
    perimeter = calculate_perimeter(meter_coords)
    usable_area = calculate_usable_area(raw_area, perimeter, setback_m, obstruction_area)
    
    azimuth_deg = calculate_dominant_azimuth(meter_coords)
    dc_capacity_kw = calculate_dc_capacity(usable_area, eff)
    ac_capacity_kw = recommend_inverter_capacity(dc_capacity_kw, dc_ac_ratio)
    
    annual_kwh = estimate_annual_yield(
        dc_capacity_kw,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        peak_sun_hours_per_day=psh,
        system_loss_factor=sys_loss
    )
    payback_years = estimate_simple_payback(
        annual_kwh,
        tariff,
        cost_per_kw=cost_per_kw,
        dc_capacity_kw=dc_capacity_kw
    )

    safe_name = "".join(c if c.isalnum() else "_" for c in address)[:30].strip('_')
    if not safe_name:
        safe_name = f"scan_{lat:.4f}_{lon:.4f}"

    out_pdf = os.path.join(out_dir, f"SolarScan_Report_{safe_name}.pdf")
    out_html = os.path.join(out_dir, f"SolarScan_Report_{safe_name}.html")

    report_data = {
        "address": address,
        "lat": lat,
        "lon": lon,
        "polygon_coords": polygon_coords,
        "meter_coords": meter_coords,
        "raw_area": raw_area,
        "perimeter": perimeter,
        "usable_area": usable_area,
        "setback_m": setback_m,
        "module_efficiency": eff,
        "dc_capacity_kw": dc_capacity_kw,
        "ac_capacity_kw": ac_capacity_kw,
        "azimuth_deg": azimuth_deg,
        "tilt_deg": tilt_deg,
        "annual_kwh": annual_kwh,
        "rate_aed": tariff,
        "payback_years": payback_years
    }

    if fmt in ("pdf", "both"):
        generate_pdf_report(report_data, out_pdf)
    if fmt in ("html", "both"):
        generate_html_report(report_data, out_html)
    
    print(f"Scan completed for '{address}':")
    print(f"  - Footprint Area: {raw_area:.2f} m² | Usable Area: {usable_area:.2f} m²")
    print(f"  - DC Capacity: {dc_capacity_kw:.2f} kW DC | Inverter: {ac_capacity_kw:.2f} kW AC")
    print(f"  - Annual Generation: {annual_kwh:,.2f} kWh/yr | Payback: {payback_years:.2f} yrs")
    if fmt in ("pdf", "both"):
        print(f"  - PDF Report: {out_pdf}")
    if fmt in ("html", "both"):
        print(f"  - HTML Report: {out_html}")
    return out_html if fmt == "html" else out_pdf


def main():
    parser = argparse.ArgumentParser(prog="solarscan", description="SolarScan Rooftop Solar Pre-Feasibility Tool")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan an address or coordinate")
    scan_parser.add_argument("address", type=str, help="Address or location label")
    scan_parser.add_argument("--lat", type=float, default=None, help="Latitude override")
    scan_parser.add_argument("--lon", type=float, default=None, help="Longitude override")
    scan_parser.add_argument("--tilt", type=float, default=None, help="Tilt angle (deg)")
    scan_parser.add_argument("--rate-aed", type=float, default=0.38, help="Tariff rate (AED/kWh)")
    scan_parser.add_argument("--module-efficiency", type=float, default=None, help="Module efficiency")
    scan_parser.add_argument("--setback", type=float, default=None, help="Setback distance (m)")
    scan_parser.add_argument("--out", type=str, default="reports", help="Output directory")
    scan_parser.add_argument("--config", type=str, default="solarscan.yaml", help="Config YAML file")
    scan_parser.add_argument("--fixture", type=str, default=None, help="Path to offline JSON fixture")
    scan_parser.add_argument("--format", choices=["pdf", "html", "both"], default="pdf", help="Report format")

    demo_parser = subparsers.add_parser("demo", help="Run offline reference case study")
    demo_parser.add_argument("--format", choices=["pdf", "html", "both"], default="pdf", help="Report format")

    batch_parser = subparsers.add_parser("batch", help="Batch scan addresses from CSV")
    batch_parser.add_argument("csv_file", type=str, help="CSV file path")
    batch_parser.add_argument("--out", type=str, default="reports", help="Output directory")
    batch_parser.add_argument("--config", type=str, default="solarscan.yaml", help="Config file")
    batch_parser.add_argument("--format", choices=["pdf", "html", "both"], default="pdf", help="Report format")

    args = parser.parse_args()

    if args.command == "scan":
        run_scan(
            address=args.address,
            lat=args.lat,
            lon=args.lon,
            tilt=args.tilt,
            rate_aed=args.rate_aed,
            module_eff=args.module_efficiency,
            setback=args.setback,
            out_dir=args.out,
            config_path=args.config,
            fixture_path=args.fixture,
            fmt=args.format
        )
    elif args.command == "demo":
        fixture = "data/fixtures/uos_w5.json"
        if not os.path.exists(fixture):
            fixture = None
        run_scan(
            address="Computer Science Department W5 Sharjah",
            fixture_path=fixture,
            lat=25.2893304,
            lon=55.4783103,
            tilt=15.0,
            rate_aed=0.38,
            out_dir="reports/demo",
            fmt=args.format
        )
    elif args.command == "batch":
        if not os.path.exists(args.csv_file):
            print(f"Error: CSV '{args.csv_file}' not found.")
            sys.exit(1)
        with open(args.csv_file, 'r', encoding='utf-8') as f:
            rows = [r for r in csv.DictReader(f) if r.get("address")]
            for idx, r in enumerate(rows, 1):
                addr = r["address"]
                lat = float(r["lat"]) if r.get("lat") and r["lat"].strip() else None
                lon = float(r["lon"]) if r.get("lon") and r["lon"].strip() else None
                print(f"[{idx}/{len(rows)}] Processing {addr}...")
                run_scan(address=addr, lat=lat, lon=lon, out_dir=args.out, config_path=args.config, fmt=args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
