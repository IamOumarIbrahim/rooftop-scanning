"""Independent check of the PVGIS yield grid with pvlib.

pvlib models the same 1 kWp system from hourly weather (PVGIS typical
meteorological year) with its own transposition (Perez), angle-of-incidence,
cell-temperature (SAPM) and PVWatts DC/AC models, plus the same 14 % loss.
If both tools agree, the yield numbers in the paper do not depend on one model.

Output: results/pvlib_crosscheck.json
Usage:  python experiments/crosscheck_pvlib.py
"""
import json
import os
import sys

import pandas as pd
import pvlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from solarscan.yield_estimate import specific_yield  # noqa: E402

LAT, LON = 25.2893, 55.4783
CACHE = os.path.join(ROOT, "data", "_cache", "pvgis_tmy_sharjah.csv")
CASES = [(0, 180), (15, 180), (25, 180), (15, 90), (15, 270), (15, 0), (30, 0)]


def weather():
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, index_col=0, parse_dates=True)
    w = pvlib.iotools.get_pvgis_tmy(LAT, LON, map_variables=True)[0]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    w.to_csv(CACHE)
    return w


def pvlib_yield(w, tilt, az):
    idx = pd.DatetimeIndex(w.index).tz_convert("UTC")
    loc = pvlib.location.Location(LAT, LON)
    sp = loc.get_solarposition(idx)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, az, sp.apparent_zenith, sp.azimuth, w.dni.values, w.ghi.values, w.dhi.values,
        dni_extra=pvlib.irradiance.get_extra_radiation(idx), model="perez",
        airmass=loc.get_airmass(idx).airmass_relative)
    aoi = pvlib.irradiance.aoi(tilt, az, sp.apparent_zenith, sp.azimuth)
    eff = (poa.poa_direct * pvlib.iam.physical(aoi) + poa.poa_diffuse).fillna(0)
    tc = pvlib.temperature.sapm_cell(poa.poa_global.fillna(0), w.temp_air.values, w.wind_speed.values,
                                     **pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_polymer"])
    pdc = pvlib.pvsystem.pvwatts_dc(eff, tc, 1000, -0.004) * (1 - 0.14)
    pac = pvlib.inverter.pvwatts(pdc, 1000 / 0.96, eta_inv_nom=0.96)
    return float(pac.clip(lower=0).sum() / 1000)


def main():
    w = weather()
    rows = []
    for tilt, az in CASES:
        a, b = specific_yield(tilt, az, "sharjah"), pvlib_yield(w, tilt, az)
        rows.append({"tilt": tilt, "azimuth": az, "pvgis": round(a, 1), "pvlib": round(b, 1),
                     "diff_pct": round((b - a) / a * 100, 2)})
        print(rows[-1])
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "pvlib_crosscheck.json"), "w", encoding="utf-8") as f:
        json.dump({"site": "sharjah", "lat": LAT, "lon": LON, "cases": rows,
                   "ghi_kwh_m2": round(float(w.ghi.sum()) / 1000), "dni_kwh_m2": round(float(w.dni.sum()) / 1000),
                   "t_air_max_c": round(float(w.temp_air.max()), 1),
                   "max_abs_diff_pct": max(abs(r["diff_pct"]) for r in rows)}, f, indent=1)


if __name__ == "__main__":
    main()
