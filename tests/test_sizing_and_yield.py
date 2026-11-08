"""Tests for solarscan.sizing and solarscan.yield_estimate."""

import math

import pytest

from solarscan.sizing import (
    calculate_dc_capacity, recommend_inverter_capacity, calculate_module_count, is_viable_system,
)
from solarscan.yield_estimate import (
    specific_yield, optimal_specific_yield, nearest_site, calculate_orientation_derate,
    estimate_annual_yield, estimate_simple_payback, calculate_lcoe, calculate_npv,
    calculate_discounted_payback, calculate_carbon_offset, calculate_specific_yield,
)


# ---------- sizing ----------

def test_dc_capacity_includes_packing_factor():
    # 100 m2 x 0.70 packing x 0.20 efficiency x 1 kW/m2 = 14 kWp
    assert math.isclose(calculate_dc_capacity(100.0, 0.20, 0.70), 14.0, rel_tol=1e-9)
    assert math.isclose(calculate_dc_capacity(100.0, 0.20, 1.0), 20.0, rel_tol=1e-9)
    assert calculate_dc_capacity(100.0, 0.20, 1.5) == 20.0  # packing factor is capped at 1


def test_inverter_and_module_count():
    assert math.isclose(recommend_inverter_capacity(20.0, 1.2), 16.67, abs_tol=0.01)
    assert calculate_module_count(20.0, 400.0) == 50


def test_sizing_edge_cases():
    assert calculate_dc_capacity(0.0) == 0.0
    assert calculate_dc_capacity(100.0, -0.05) == 0.0
    assert recommend_inverter_capacity(0.0, 1.2) == 0.0
    assert recommend_inverter_capacity(100.0, 0.0) == 100.0
    assert calculate_module_count(0.0) == 0
    assert calculate_module_count(10.0, 0.0) == 0
    assert is_viable_system(10.0) and not is_viable_system(1.5)


# ---------- yield (PVGIS grids) ----------

def test_south_yield_in_uae_range():
    # PVGIS and an independent pvlib run both give ~1,700 kWh/kWp at 15 deg south in Sharjah.
    assert 1600 < specific_yield(15, 180, "sharjah") < 1800


def test_flat_panel_has_no_azimuth_effect():
    values = {specific_yield(0, az) for az in range(0, 360, 30)}
    assert len(values) == 1


def test_orientation_ordering():
    s, e, w, n = (specific_yield(15, a) for a in (180, 90, 270, 0))
    assert s > e > n and s > w > n
    assert 0.80 < e / s < 0.95  # east loses about 10 % at 15 deg tilt, not 30 %


def test_interpolation_is_continuous_and_periodic():
    assert math.isclose(specific_yield(15, 0), specific_yield(15, 360), rel_tol=1e-9)
    a, b, c = specific_yield(15, 180), specific_yield(15, 187.5), specific_yield(15, 195)
    assert min(a, c) - 1e-6 <= b <= max(a, c) + 1e-6
    assert specific_yield(-5, 180) == specific_yield(0, 180)       # tilt clamped
    assert specific_yield(90, 180) == specific_yield(40, 180)


def test_derate_and_annual_yield():
    assert math.isclose(calculate_orientation_derate(180, 25), specific_yield(25, 180) / optimal_specific_yield(), rel_tol=1e-3)
    assert 0 < calculate_orientation_derate(0, 30) < calculate_orientation_derate(180, 15) <= 1
    assert math.isclose(estimate_annual_yield(10, 15, 180), 10 * specific_yield(15, 180), rel_tol=1e-6)
    assert estimate_annual_yield(0, 15, 180) == 0.0


def test_nearest_site():
    assert nearest_site(25.29, 55.48) in ("sharjah", "ajman")
    assert nearest_site(24.35, 54.52) in ("abu_dhabi", "sharjah", "dubai")


def test_unknown_site_raises():
    with pytest.raises(FileNotFoundError):
        specific_yield(15, 180, "atlantis")


# ---------- economics ----------

def test_simple_payback_closed_form():
    # 10 kWp x 3,000 AED = 30,000 AED; 17,000 kWh x 0.38 = 6,460 AED/yr -> 4.64 yr
    assert math.isclose(estimate_simple_payback(17000, 0.38, 3000, 10), 4.64, abs_tol=0.01)


def test_npv_closed_form_annuity():
    # No degradation, no O&M, no escalation: NPV = -C + S * (1 - (1+d)^-n) / d
    npv = calculate_npv(10000, 0.4, 10, cost_per_kw=3000, discount_rate=0.05, lifetime_years=25,
                        om_cost_fraction=0, annual_degradation=0)
    expected = -30000 + 4000 * (1 - 1.05 ** -25) / 0.05
    assert math.isclose(npv, expected, abs_tol=0.01)


def test_lcoe_closed_form():
    lcoe = calculate_lcoe(10000, 10, cost_per_kw=3000, discount_rate=0.05, lifetime_years=25,
                          om_cost_fraction=0, annual_degradation=0)
    assert math.isclose(lcoe, 30000 / (10000 * (1 - 1.05 ** -25) / 0.05), abs_tol=1e-4)


def test_discounted_payback_longer_than_simple():
    simple = estimate_simple_payback(17000, 0.38, 3000, 10)
    disc = calculate_discounted_payback(17000, 0.38, 10, cost_per_kw=3000, om_cost_fraction=0)
    assert disc > simple


def test_specific_yield_and_carbon():
    assert calculate_specific_yield(16000, 10) == 1600
    assert calculate_specific_yield(1000, 0) == 0
    assert math.isclose(calculate_carbon_offset(260000, 0.42), 109.2, abs_tol=0.01)
    assert calculate_carbon_offset(0) == 0


def test_financial_edge_cases():
    assert estimate_simple_payback(0.0, 0.38) == float("inf")
    assert calculate_lcoe(0.0, 10.0) == float("inf")
    assert calculate_npv(1000.0, 0.38, 0.0) == 0.0
    assert calculate_discounted_payback(0.0, 0.38, 0.0) == 0.0
    assert calculate_discounted_payback(0.0, 0.38, 10.0) == float("inf")
    assert calculate_discounted_payback(10.0, 0.01, 1000.0) == float("inf")
    for fn, args in ((calculate_lcoe, (1000.0, 10.0)), (calculate_npv, (1000.0, 0.38, 10.0)),
                     (calculate_discounted_payback, (1000.0, 0.38, 10.0))):
        with pytest.raises(ValueError, match="Discount rate"):
            fn(*args, discount_rate=-1.0)
