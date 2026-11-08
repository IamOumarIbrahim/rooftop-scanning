"""
Command line interface (CLI) for SolarScan rooftop pre-feasibility framework.
"""

import argparse
import re
import os
import sys
import csv
from typing import Dict, Any, Optional

from solarscan.osm import geocode_address, query_osm_building
from solarscan.fixtures import load_fixture
from solarscan.geometry import (
    latlon_to_meters, calculate_shoelace_area, calculate_perimeter,
    calculate_usable_area_buffered, calculate_building_axis, array_azimuth_aligned, usable_polygon
)
from solarscan.layout import layout_modules
from solarscan.sizing import recommend_inverter_capacity
from solarscan.yield_estimate import estimate_annual_yield, estimate_simple_payback, nearest_site
from solarscan.report import generate_pdf_report, generate_html_report
from solarscan.config import load_config, get_emirate_profile


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
    fmt: str = "pdf",
    emirate: Optional[str] = None,
    cost_per_kw: Optional[float] = None,
    return_data: bool = False,
):
    """Executes end-to-end solar pre-feasibility screening.

    Returns the report path, or with return_data=True the full result dict (with 'pdf'/'html' paths)."""
    cfg = load_config(config_path, emirate=emirate)
    
    tilt_deg = tilt if tilt is not None else cfg.get("default_tilt_deg", 15.0)
    setback_m = setback if setback is not None else cfg.get("setback_m", 1.5)
    eff = module_eff if module_eff is not None else cfg.get("module_efficiency", 0.20)
    dc_ac_ratio = cfg.get("dc_ac_ratio", 1.2)
    packing = cfg.get("packing_factor", 0.70)
    layout = cfg.get("array_layout", "south")
    tariff = rate_aed if rate_aed is not None else cfg.get("rate_aed", 0.38)
    cost_per_kw = cost_per_kw if cost_per_kw is not None else cfg.get("cost_per_kw", 3000.0)

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
    usable_area = calculate_usable_area_buffered(meter_coords, setback_m, obstruction_area)

    building_axis_deg = calculate_building_axis(meter_coords)
    azimuth_deg = 180.0 if layout == "south" else array_azimuth_aligned(building_axis_deg)
    site = cfg["pvgis_site"] if emirate else nearest_site(lat, lon)
    # Size the system from the modules that actually fit in tilted rows (GCR = packing factor).
    w_m, l_m = cfg.get("module_width_m", 1.0), cfg.get("module_length_m", 2.0)
    usable_poly = usable_polygon(meter_coords, setback_m)
    rows = layout_modules(usable_poly, w_m, l_m, tilt_deg, packing, azimuth_deg)
    module_kw = eff * w_m * l_m  # kWp per module at 1 kW/m^2
    dc_capacity_kw = round(rows["n"] * module_kw, 3)
    if obstruction_area > 0:  # known inner courtyards/holes reduce the array in proportion
        dc_capacity_kw = round(dc_capacity_kw * max(0.0, 1 - obstruction_area / max(usable_area, 1e-9)), 3)
    ac_capacity_kw = recommend_inverter_capacity(dc_capacity_kw, dc_ac_ratio)

    annual_kwh = estimate_annual_yield(dc_capacity_kw, tilt_deg=tilt_deg, azimuth_deg=azimuth_deg, site=site)
    payback_years = estimate_simple_payback(
        annual_kwh,
        tariff,
        cost_per_kw=cost_per_kw,
        dc_capacity_kw=dc_capacity_kw
    )

    safe_name = re.sub(r"[^0-9A-Za-z]+", "_", address).strip("_")[:40].rstrip("_")
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
        "building_axis_deg": building_axis_deg,
        "array_layout": layout,
        "pvgis_site": site,
        "packing_factor": packing,
        "n_modules": rows["n"],
        "modules": rows["modules"],
        "usable_rings": [list(g.exterior.coords) for g in (getattr(usable_poly, "geoms", None) or [usable_poly])
                         if not g.is_empty],
        "module_w": module_kw * 1000,
        "module_width_m": w_m,
        "module_length_m": l_m,
        "row_pitch_m": rows.get("pitch_m"),
        "dc_ac_ratio": dc_ac_ratio,
        "osm_way_id": osm_data.get("building_id"),
        "cost_per_kw": cost_per_kw,
        "discount_rate": cfg.get("discount_rate", 0.05),
        "lifetime_years": cfg.get("lifetime_years", 25),
        "annual_degradation": cfg.get("annual_degradation", 0.005),
        "om_cost_fraction": cfg.get("om_cost_fraction", 0.015),
        "version": __import__("solarscan").__version__,
        "tilt_deg": tilt_deg,
        "annual_kwh": annual_kwh,
        "rate_aed": tariff,
        "payback_years": payback_years,
        "emirate": cfg.get("emirate"),
        "utility": cfg.get("utility"),
        "grid_co2_kg_per_kwh": cfg.get("grid_co2_kg_per_kwh", 0.42)
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
    if return_data:
        report_data["pdf"] = out_pdf if fmt in ("pdf", "both") else None
        report_data["html"] = out_html if fmt in ("html", "both") else None
        return report_data
    return out_html if fmt == "html" else out_pdf


def run_batch_scan(
    csv_file: str,
    out_dir: str = "reports",
    config_path: str = "solarscan.yaml",
    fmt: str = "pdf"
) -> list:
    """
    Executes batch pre-feasibility scans from a CSV file.
    Handles per-row errors defensively without terminating batch progress.
    """
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Batch CSV '{csv_file}' not found.")

    generated_reports = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("address") and r["address"].strip()]

    for idx, r in enumerate(rows, 1):
        addr = r["address"].strip()
        lat_raw = r.get("lat")
        lon_raw = r.get("lon")
        emirate = r.get("emirate", "").strip() or None
        fixture = r.get("fixture", "").strip() or None

        lat = None
        lon = None
        if lat_raw and lon_raw:
            try:
                lat = float(lat_raw.strip())
                lon = float(lon_raw.strip())
            except ValueError:
                print(f"Warning: Skipping invalid coordinates for '{addr}': lat={lat_raw}, lon={lon_raw}")
                lat, lon = None, None

        print(f"[{idx}/{len(rows)}] Processing {addr}...")
        try:
            out_file = run_scan(
                address=addr,
                lat=lat,
                lon=lon,
                out_dir=out_dir,
                config_path=config_path,
                fixture_path=fixture,
                fmt=fmt,
                emirate=emirate
            )
            generated_reports.append(out_file)
        except Exception as e:
            print(f"Warning: Failed processing '{addr}': {e}")

    return generated_reports


# Offline demo: a warehouse in Dubai (OSM way 175844238), shipped with the package
DEMO_CASE = dict(address="TCTI warehouse, Al Quoz Industrial Area 2, Dubai", lat=25.14659, lon=55.23921,
                 emirate="dubai", fixture=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                                                       "demo_tcti.json"))


def demo_kwargs():
    """run_scan arguments for the offline demo building."""
    c = DEMO_CASE
    return dict(address=c["address"], lat=c["lat"], lon=c["lon"], emirate=c["emirate"],
                fixture_path=c["fixture"] if os.path.exists(c["fixture"]) else None)


def main():
    parser = argparse.ArgumentParser(prog="solarscan", description="SolarScan Rooftop Solar Pre-Feasibility Tool")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan an address or coordinate")
    scan_parser.add_argument("address", type=str, help="Address or location label")
    scan_parser.add_argument("--lat", type=float, default=None, help="Latitude override")
    scan_parser.add_argument("--lon", type=float, default=None, help="Longitude override")
    scan_parser.add_argument("--tilt", type=float, default=None, help="Tilt angle (deg)")
    scan_parser.add_argument("--rate-aed", type=float, default=None, help="Tariff rate (AED/kWh)")
    scan_parser.add_argument("--cost", type=float, default=None, help="Installed cost (AED/kWp)")
    scan_parser.add_argument("--module-efficiency", type=float, default=None, help="Module efficiency")
    scan_parser.add_argument("--setback", type=float, default=None, help="Setback distance (m)")
    scan_parser.add_argument("--out", type=str, default="reports", help="Output directory")
    scan_parser.add_argument("--config", type=str, default="solarscan.yaml", help="Config YAML file")
    scan_parser.add_argument("--fixture", type=str, default=None, help="Path to offline JSON fixture")
    scan_parser.add_argument("--format", choices=["pdf", "html", "both"], default="pdf", help="Report format")
    scan_parser.add_argument("--emirate", type=str, default=None, choices=["sharjah", "dubai", "abu_dhabi", "ajman", "ras_al_khaimah", "fujairah", "umm_al_quwain"], help="Regional UAE utility profile")

    gui_parser = subparsers.add_parser("gui", help="Open the graphical interface")
    gui_parser.add_argument("--screenshot", type=str, default=None, help=argparse.SUPPRESS)

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
            fmt=args.format,
            emirate=args.emirate,
            cost_per_kw=args.cost
        )
    elif args.command == "gui":
        from solarscan.gui import main as gui_main
        gui_main(screenshot=args.screenshot)
    elif args.command == "demo":
        run_scan(**demo_kwargs(), out_dir="reports/demo", fmt=args.format)
    elif args.command == "batch":
        try:
            run_batch_scan(
                csv_file=args.csv_file,
                out_dir=args.out,
                config_path=args.config,
                fmt=args.format
            )
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
