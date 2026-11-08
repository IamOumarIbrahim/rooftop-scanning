"""
Energy yield and economics for rooftop PV pre-feasibility screening.

Yield comes from PVGIS (EU JRC) specific-yield grids stored in solarscan/data/pvgis/.
Each grid gives annual AC energy per kWp (kWh/kWp/yr) for tilts 0-40 deg and
azimuths 0-345 deg at one site per emirate. PVGIS already includes irradiance,
temperature, angle-of-incidence and spectral effects, plus a 14 % system loss
(wiring, inverter, soiling, mismatch). We interpolate bilinearly between grid points.

All money values are in UAE dirham (AED).
"""

import functools
import json
import math
import os
from typing import Dict, Optional

PVGIS_DIR = os.path.join(os.path.dirname(__file__), "data", "pvgis")
DEFAULT_SITE = "sharjah"


@functools.lru_cache(maxsize=None)
def load_yield_grid(site: str = DEFAULT_SITE) -> Dict:
    """Loads the stored PVGIS grid for one site (emirate key, e.g. 'sharjah')."""
    path = os.path.join(PVGIS_DIR, f"{site}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No PVGIS grid for site '{site}' ({path}). Run experiments/fetch_pvgis.py.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def available_sites() -> list:
    if not os.path.isdir(PVGIS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(PVGIS_DIR) if f.endswith(".json"))


def nearest_site(lat: float, lon: float) -> str:
    """Returns the stored PVGIS site closest to (lat, lon)."""
    best, best_d = DEFAULT_SITE, float("inf")
    for s in available_sites():
        g = load_yield_grid(s)
        d = math.hypot(g["lat"] - lat, (g["lon"] - lon) * math.cos(math.radians(lat)))
        if d < best_d:
            best, best_d = s, d
    return best


def specific_yield(tilt_deg: float = 15.0, azimuth_deg: float = 180.0, site: str = DEFAULT_SITE) -> float:
    """
    Annual AC energy per installed kWp (kWh/kWp/yr) for a fixed array.
    Azimuth: 0 = North, 90 = East, 180 = South, 270 = West.
    """
    g = load_yield_grid(site)
    tilts, azs, sy = g["tilts"], g["azimuths"], g["specific_yield"]
    t = max(tilts[0], min(tilts[-1], float(tilt_deg)))
    a = float(azimuth_deg) % 360.0

    i = min(range(len(tilts) - 1), key=lambda k: 0 if tilts[k] <= t <= tilts[k + 1] else 1)
    t0, t1 = tilts[i], tilts[i + 1]
    wt = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)

    step = azs[1] - azs[0]
    j = int(a // step) % len(azs)
    a0, a1 = azs[j], azs[(j + 1) % len(azs)]
    wa = (a - a0) / step

    def v(tt, aa):
        return sy[str(tt)][str(aa)]

    top = v(t0, a0) * (1 - wa) + v(t0, a1) * wa
    bot = v(t1, a0) * (1 - wa) + v(t1, a1) * wa
    return round(top * (1 - wt) + bot * wt, 2)


def optimal_specific_yield(site: str = DEFAULT_SITE) -> float:
    g = load_yield_grid(site)
    return max(max(row.values()) for row in g["specific_yield"].values())


def calculate_orientation_derate(azimuth_deg: float, tilt_deg: float, site: str = DEFAULT_SITE) -> float:
    """Yield at (tilt, azimuth) divided by the best yield at the site, in (0, 1]."""
    return round(specific_yield(tilt_deg, azimuth_deg, site) / optimal_specific_yield(site), 4)


def estimate_annual_yield(
    dc_capacity_kw: float,
    tilt_deg: float = 15.0,
    azimuth_deg: float = 180.0,
    site: str = DEFAULT_SITE,
) -> float:
    """
    Annual AC energy in kWh/yr:  E = P_dc * Y(tilt, azimuth, site)
    where Y is the PVGIS specific yield in kWh/kWp/yr.
    """
    if dc_capacity_kw <= 0.0:
        return 0.0
    return round(dc_capacity_kw * specific_yield(tilt_deg, azimuth_deg, site), 2)


def calculate_specific_yield(annual_kwh: float, dc_capacity_kw: float) -> float:
    """Specific yield in kWh/kWp/yr."""
    if dc_capacity_kw <= 0.0:
        return 0.0
    return round(annual_kwh / dc_capacity_kw, 2)


def estimate_simple_payback(
    annual_kwh: float,
    rate_per_kwh: float,
    cost_per_kw: float = 3000.0,
    dc_capacity_kw: float = 10.0,
) -> float:
    """
    Simple payback in years:  T = (P_dc * c) / (E * r)
    cost_per_kw: installed cost in AED per kWp. rate_per_kwh: tariff in AED/kWh.
    """
    annual_savings = annual_kwh * rate_per_kwh
    if annual_savings <= 0:
        return float("inf")
    return round(dc_capacity_kw * cost_per_kw / annual_savings, 2)


def _cash_flows(annual_kwh, tariff, capex, years, om_frac, degradation, tariff_esc, om_esc):
    for year in range(1, years + 1):
        energy = annual_kwh * (1.0 - degradation) ** (year - 1)
        revenue = energy * tariff * (1.0 + tariff_esc) ** (year - 1)
        om = capex * om_frac * (1.0 + om_esc) ** (year - 1)
        yield year, energy, revenue - om


def calculate_lcoe(
    annual_kwh: float,
    dc_capacity_kw: float,
    cost_per_kw: float = 3000.0,
    discount_rate: float = 0.05,
    lifetime_years: int = 25,
    om_cost_fraction: float = 0.015,
    annual_degradation: float = 0.005,
) -> float:
    """
    Levelized cost of electricity (AED/kWh):
        LCOE = [CAPEX + sum O&M_t/(1+d)^t] / [sum E_t/(1+d)^t]
    """
    if discount_rate <= -1.0:
        raise ValueError(f"Discount rate must be greater than -1.0, got {discount_rate}")
    if annual_kwh <= 0.0 or dc_capacity_kw <= 0.0:
        return float("inf")
    capex = dc_capacity_kw * cost_per_kw
    costs, energy = capex, 0.0
    for year in range(1, lifetime_years + 1):
        df = (1.0 + discount_rate) ** year
        costs += capex * om_cost_fraction / df
        energy += annual_kwh * (1.0 - annual_degradation) ** (year - 1) / df
    return round(costs / energy, 4)


def calculate_npv(
    annual_kwh: float,
    tariff_per_kwh: float,
    dc_capacity_kw: float,
    cost_per_kw: float = 3000.0,
    discount_rate: float = 0.05,
    lifetime_years: int = 25,
    om_cost_fraction: float = 0.015,
    annual_degradation: float = 0.005,
    tariff_escalation: float = 0.0,
    om_escalation: float = 0.0,
) -> float:
    """Net present value (AED) of bill savings minus O&M, less up-front CAPEX."""
    if discount_rate <= -1.0:
        raise ValueError(f"Discount rate must be greater than -1.0, got {discount_rate}")
    if dc_capacity_kw <= 0.0:
        return 0.0
    capex = dc_capacity_kw * cost_per_kw
    npv = -capex
    for year, _, cf in _cash_flows(annual_kwh, tariff_per_kwh, capex, lifetime_years,
                                   om_cost_fraction, annual_degradation, tariff_escalation, om_escalation):
        npv += cf / (1.0 + discount_rate) ** year
    return round(npv, 2)


def calculate_discounted_payback(
    annual_kwh: float,
    tariff_per_kwh: float,
    dc_capacity_kw: float,
    cost_per_kw: float = 3000.0,
    discount_rate: float = 0.05,
    lifetime_years: int = 25,
    om_cost_fraction: float = 0.015,
    annual_degradation: float = 0.005,
) -> float:
    """Years until cumulative discounted net savings repay CAPEX (inf if never)."""
    if discount_rate <= -1.0:
        raise ValueError(f"Discount rate must be greater than -1.0, got {discount_rate}")
    if dc_capacity_kw <= 0.0:
        return 0.0
    if annual_kwh <= 0.0 or tariff_per_kwh <= 0.0:
        return float("inf")
    capex = dc_capacity_kw * cost_per_kw
    cum = -capex
    for year, _, cf in _cash_flows(annual_kwh, tariff_per_kwh, capex, lifetime_years,
                                   om_cost_fraction, annual_degradation, 0.0, 0.0):
        dcf = cf / (1.0 + discount_rate) ** year
        if dcf > 0 and cum + dcf >= 0:
            return round(year - 1 + (-cum) / dcf, 2)
        cum += dcf
    return float("inf")


def calculate_carbon_offset(annual_kwh: float, grid_emission_factor_kg_per_kwh: float = 0.42) -> float:
    """Avoided emissions in tCO2e/yr = E * EF / 1000."""
    if annual_kwh <= 0.0 or grid_emission_factor_kg_per_kwh <= 0.0:
        return 0.0
    return round(annual_kwh * grid_emission_factor_kg_per_kwh / 1000.0, 2)
