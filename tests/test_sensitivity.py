"""
Unit tests for experiments.run_sensitivity module.
"""

import pytest
import math
from experiments.run_sensitivity import (
    run_setback_sensitivity,
    run_orientation_sensitivity,
    run_economic_sensitivity,
    run_degradation_sensitivity,
    run_monte_carlo_uncertainty
)


def test_setback_sensitivity():
    res = run_setback_sensitivity()
    assert "setbacks" in res
    assert "residential" in res
    assert "institutional" in res
    assert "commercial" in res
    for key in ["residential", "institutional", "commercial"]:
        data = res[key]
        assert data["pa_ratio"] > 0
        fractions = data["usable_fractions"]
        # Setback 0m must yield 100% usable
        assert math.isclose(fractions[0], 1.0, rel_tol=1e-3)
        # Larger setbacks must monotonically decrease usable fraction
        assert all(f >= 0.0 for f in fractions)
        assert fractions[-1] <= fractions[0]


def test_orientation_sensitivity():
    res = run_orientation_sensitivity()
    assert 20 in res["tilts"]
    yields_20 = res["yields"][20]
    # Optimal yield should occur at South (180 deg, index 12 in 0:360:15)
    max_idx = yields_20.index(max(yields_20))
    optimal_azimuth = res["azimuths"][max_idx]
    assert optimal_azimuth == 180


def test_economic_sensitivity():
    res = run_economic_sensitivity()
    table = res["payback_table"]
    assert 1000.0 in table
    # Higher tariff must decrease payback period
    pbs = table[1000.0]
    assert pbs[0] > pbs[-1]


def test_degradation_sensitivity():
    res = run_degradation_sensitivity(initial_kwh=260330.0)
    totals = res["lifetime_mwh"]
    # 0.3% degradation should produce higher lifetime total than 1.0%
    assert totals[0.003] > totals[0.010]


def test_monte_carlo_uncertainty():
    res = run_monte_carlo_uncertainty(n_iterations=500, random_seed=42)
    assert res["yield_mwh_p5"] <= res["yield_mwh_p50"] <= res["yield_mwh_p95"]
    assert res["payback_yrs_p5"] <= res["payback_yrs_p50"] <= res["payback_yrs_p95"]
    assert 200.0 <= res["yield_mwh_p50"] <= 300.0
    assert 2.0 <= res["payback_yrs_p50"] <= 4.0
