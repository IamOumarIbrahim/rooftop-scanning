"""
Unit tests for solarscan.sizing and solarscan.yield_estimate modules.
"""

import pytest
import math
from solarscan.sizing import (
    calculate_dc_capacity,
    recommend_inverter_capacity,
    calculate_module_count
)
from solarscan.yield_estimate import (
    calculate_orientation_derate,
    estimate_annual_yield,
    estimate_simple_payback,
    calculate_lcoe
)


def test_dc_capacity_formula():
    """
    Verifies DC capacity formula:
    Usable area = 100 m2, efficiency = 0.20 -> 20.0 kW DC.
    """
    cap = calculate_dc_capacity(100.0, module_efficiency=0.20)
    assert math.isclose(cap, 20.0, rel_tol=1e-5)


def test_inverter_recommendation():
    """
    Verifies inverter recommendation:
    DC capacity = 20.0 kW, DC/AC ratio = 1.2 -> 16.67 kW AC.
    """
    inv = recommend_inverter_capacity(20.0, dc_ac_ratio=1.2)
    assert math.isclose(inv, 16.67, abs_tol=0.01)


def test_module_count():
    """Verifies module count calculation."""
    count = calculate_module_count(20.0, module_rating_watts=400.0)
    assert count == 50


def test_optimal_orientation_derate():
    """Optimal South orientation (180 deg) and 20 deg tilt yields factor 1.0."""
    derate = calculate_orientation_derate(180.0, 20.0)
    assert math.isclose(derate, 1.0, abs_tol=1e-3)


def test_orientation_derate_bounds():
    """Verifies that derate factor remains in [0.5, 1.0]."""
    for az in [0, 90, 180, 270]:
        for tilt in [0, 15, 30, 45]:
            d = calculate_orientation_derate(az, tilt)
            assert 0.5 <= d <= 1.0


def test_annual_yield_calculation():
    """
    Verifies annual generation:
    10 kW DC, 5.5 PSH, 365 days, derate=1.0, loss=0.85 -> 17,063.75 kWh/yr.
    """
    kwh = estimate_annual_yield(
        10.0,
        tilt_deg=20.0,
        azimuth_deg=180.0,
        peak_sun_hours_per_day=5.5,
        system_loss_factor=0.85
    )
    expected = 10.0 * 5.5 * 365.0 * 1.0 * 0.85
    assert math.isclose(kwh, expected, rel_tol=1e-4)


def test_simple_payback():
    """
    Verifies simple payback:
    CAPEX = 10 kW * 1000 $/kW = $10,000.
    Annual savings = 17,063.75 kWh * 0.10 $/kWh = $1,706.38.
    Payback = 10,000 / 1706.38 = 5.86 years.
    """
    payback = estimate_simple_payback(
        annual_kwh=17063.75,
        rate_per_kwh=0.10,
        cost_per_kw=1000.0,
        dc_capacity_kw=10.0
    )
    assert math.isclose(payback, 5.86, abs_tol=0.02)


def test_lcoe_calculation():
    """Verifies LCOE produces realistic positive values."""
    lcoe = calculate_lcoe(
        annual_kwh=17000.0,
        dc_capacity_kw=10.0,
        cost_per_kw=1000.0,
        discount_rate=0.05,
        lifetime_years=25
    )
    assert 0.03 <= lcoe <= 0.10
