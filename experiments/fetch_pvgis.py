"""Download PVGIS specific-yield grids (kWh/kWp/yr vs tilt and azimuth) for one site per emirate.

PVGIS (EU JRC) uses satellite irradiance (SARAH-3) and a PV model with temperature,
angle-of-incidence and spectral losses. We store the grids in solarscan/data/pvgis/ so the
solarscan yield model runs offline and gives the same numbers every time.

Usage:  python experiments/fetch_pvgis.py
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "solarscan", "data", "pvgis")
API = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
SYSTEM_LOSS_PCT = 14.0  # PVGIS default: wiring, inverter, soiling, mismatch

SITES = {
    "sharjah": (25.2893, 55.4783),
    "dubai": (25.1460, 55.2310),
    "abu_dhabi": (24.3480, 54.5220),
    "ajman": (25.3920, 55.4790),
    "ras_al_khaimah": (25.7725, 55.9525),
}
TILTS = list(range(0, 41, 5))
AZIMUTHS = list(range(0, 360, 15))  # compass convention: 0 = N, 90 = E, 180 = S


def query(lat, lon, tilt, az):
    aspect = az - 180  # PVGIS: 0 = S, -90 = E, 90 = W
    if aspect > 180:
        aspect -= 360
    params = dict(lat=lat, lon=lon, peakpower=1, loss=SYSTEM_LOSS_PCT, angle=tilt,
                  aspect=aspect, outputformat="json")
    for attempt in range(6):
        try:
            r = requests.get(API, params=params, timeout=60)
            if r.ok:
                j = r.json()
                return j["outputs"]["totals"]["fixed"]["E_y"], j["inputs"]["meteo_data"]
        except requests.RequestException:
            pass
        time.sleep(2 + 2 * attempt)
    raise RuntimeError(f"PVGIS failed for {lat},{lon},{tilt},{az}")


def main():
    os.makedirs(OUT, exist_ok=True)
    for site, (lat, lon) in SITES.items():
        path = os.path.join(OUT, f"{site}.json")
        if os.path.exists(path):
            print("cached", path)
            continue
        jobs = [(t, a) for t in TILTS for a in (AZIMUTHS if t > 0 else [180])]
        with ThreadPoolExecutor(max_workers=4) as ex:
            res = list(ex.map(lambda ta: query(lat, lon, *ta), jobs))
        grid = {}
        for (t, a), (ey, _) in zip(jobs, res):
            grid.setdefault(str(t), {})[str(a)] = ey
        grid["0"] = {str(a): grid["0"]["180"] for a in AZIMUTHS}  # flat panel: azimuth has no effect
        meta = res[0][1]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"site": site, "lat": lat, "lon": lon, "source": "PVGIS v5.3 PVcalc",
                       "radiation_db": meta.get("radiation_db"), "year_min": meta.get("year_min"),
                       "year_max": meta.get("year_max"), "system_loss_pct": SYSTEM_LOSS_PCT,
                       "technology": "crystSi", "units": "kWh/kWp/yr", "tilts": TILTS,
                       "azimuths": AZIMUTHS, "specific_yield": grid}, f, indent=1)
        print("wrote", path)


if __name__ == "__main__":
    main()
