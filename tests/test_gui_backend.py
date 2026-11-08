"""The desktop interface calls run_scan(return_data=True); check that path without opening a window."""
import os

from solarscan.cli import demo_kwargs, run_scan


def test_run_scan_returns_data_for_gui(tmp_path):
    d = run_scan(**demo_kwargs(), out_dir=str(tmp_path), fmt="both", cost_per_kw=2500.0, return_data=True)
    assert d["osm_way_id"] == 175844238 and d["pvgis_site"] == "dubai"  # packaged demo, not a live lookup
    assert os.path.exists(d["pdf"]) and os.path.exists(d["html"])
    assert d["cost_per_kw"] == 2500.0 and d["n_modules"] > 0
    assert abs(d["row_pitch_m"] - 2.0 / 0.70) < 1e-9
    # payback follows the cost override: cost / (specific yield * price)
    assert abs(d["payback_years"] - 2500.0 * d["dc_capacity_kw"] / (d["annual_kwh"] * d["rate_aed"])) < 0.01
