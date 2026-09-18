"""
Unit tests for experiments.run_validation module.
"""

import os
import pytest
import math
from experiments.run_validation import compute_metrics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MASTER_CSV = os.path.join(ROOT, "data", "validation_buildings.csv")


def test_master_validation_metrics():
    """Verifies that master dataset reproduces exact published research contract metrics."""
    res = compute_metrics(MASTER_CSV)
    assert res["n_buildings"] == 24
    assert math.isclose(res["mape"], 4.54, abs_tol=0.05)
    assert math.isclose(res["mbe"], -4.54, abs_tol=0.05)
    assert res["r2"] >= 0.999
    assert math.isclose(res["rmse"], 1432.71, abs_tol=1.0)
    assert "medape" in res
    assert "ci95_mbe" in res
    # 95% CI should enclose MBE
    low, high = res["ci95_mbe"]
    assert low <= res["mbe"] <= high


def test_validation_file_not_found():
    with pytest.raises(FileNotFoundError):
        compute_metrics("non_existent_path.csv")


def test_validation_synthetic_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "id,name,category,emirate,osm_area_m2,reference_area_m2,abs_error_m2,rel_error_pct\n"
        "b1,Building 1,Commercial,Sharjah,100.0,100.0,0.0,0.0\n"
        "b2,Building 2,Commercial,Sharjah,200.0,200.0,0.0,0.0\n",
        encoding="utf-8"
    )
    res = compute_metrics(str(csv_file))
    assert res["n_buildings"] == 2
    assert res["mape"] == 0.0
    assert res["mbe"] == 0.0
    assert res["r2"] == 1.0
