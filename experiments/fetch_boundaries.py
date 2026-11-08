"""Download boundaries for the location map from geoBoundaries (ODbL, source: OpenStreetMap).

UAE emirates (ADM1) and the outlines of neighboring countries (ADM0), simplified versions.
Saved to data/_cache/boundaries/ (not committed).

Usage:  python experiments/fetch_boundaries.py
"""
import os

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "_cache", "boundaries")
LAYERS = {"are_adm1": ("ARE", "ADM1"), "omn_adm0": ("OMN", "ADM0"), "sau_adm0": ("SAU", "ADM0"), "qat_adm0": ("QAT", "ADM0")}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (iso, level) in LAYERS.items():
        meta = requests.get(f"https://www.geoboundaries.org/api/current/gbOpen/{iso}/{level}/", timeout=60).json()
        with open(os.path.join(OUT, name + ".geojson"), "wb") as f:
            f.write(requests.get(meta["simplifiedGeometryGeoJSON"], timeout=300).content)
        print(name, meta.get("boundaryLicense"), meta.get("boundarySource"))


if __name__ == "__main__":
    main()
