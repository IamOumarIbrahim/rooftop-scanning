"""Match each benchmark building to Microsoft Global ML Building Footprints.

Microsoft footprints are traced by a neural network from satellite imagery
(github.com/microsoft/GlobalMLBuildingFootprints, ODbL). They are independent
of OSM, so they give a second, reproducible reference. They are not ground truth:
the model sometimes merges touching buildings or splits one roof into parts.

For each building we keep the single Microsoft polygon with the highest
intersection-over-union (IoU) with the OSM polygon, and save it to
data/reference_ms/<id>.geojson.

Usage:  python experiments/fetch_ms_footprints.py
"""
import csv
import gzip
import json
import math
import os

import requests
from shapely.geometry import Polygon, mapping, shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "reference_ms")
CACHE = os.path.join(ROOT, "data", "_cache", "ms_tiles")
LINKS = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"


def quadkey(lat, lon, z=9):
    s = math.sin(math.radians(lat))
    x = (lon + 180) / 360
    y = 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)
    tx, ty = int(x * 2 ** z), int(y * 2 ** z)
    return "".join(str((1 if tx & (1 << (i - 1)) else 0) + (2 if ty & (1 << (i - 1)) else 0))
                   for i in range(z, 0, -1))


def tile_polygons(qk, links):
    polys = []
    for i, url in enumerate(links.get(qk, [])):
        f = os.path.join(CACHE, f"{qk}_{i}.csv.gz")
        if not os.path.exists(f):
            with open(f, "wb") as fh:
                fh.write(requests.get(url, timeout=600).content)
        with gzip.open(f, "rt", encoding="utf-8") as g:
            for line in g:
                try:
                    polys.append(shape(json.loads(line)["geometry"]))
                except (ValueError, KeyError):
                    continue
    return polys


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    links_file = os.path.join(CACHE, "dataset-links.csv")
    if not os.path.exists(links_file):
        with open(links_file, "wb") as fh:
            fh.write(requests.get(LINKS, timeout=120).content)
    links = {}
    with open(links_file, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["Location"] == "UnitedArabEmirates":
                links.setdefault(row["QuadKey"], []).append(row["Url"])

    with open(os.path.join(ROOT, "data", "buildings.csv"), encoding="utf-8") as fh:
        ids = [r["id"] for r in csv.DictReader(fh)]

    tiles = {}
    for bid in ids:
        with open(os.path.join(ROOT, "data", "fixtures", bid + ".json"), encoding="utf-8") as fh:
            osm = Polygon([(c[1], c[0]) for c in json.load(fh)["polygon_coords"]])
        qk = quadkey(osm.centroid.y, osm.centroid.x)
        if qk not in tiles:
            tiles[qk] = tile_polygons(qk, links)
        cands = [p for p in tiles[qk] if p.intersects(osm)]
        path = os.path.join(OUT, bid + ".geojson")
        if not cands:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"type": "FeatureCollection", "features": []}, fh)
            print(f"{bid}: no Microsoft footprint")
            continue
        best = max(cands, key=lambda p: p.intersection(osm).area / p.union(osm).area)
        iou = best.intersection(osm).area / best.union(osm).area
        feat = {"type": "Feature", "geometry": mapping(best),
                "properties": {"id": bid, "iou_with_osm": round(iou, 4), "n_intersecting": len(cands),
                               "source": "Microsoft Global ML Building Footprints (2026-02-03 release)"}}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"type": "FeatureCollection", "features": [feat]}, fh)
        print(f"{bid}: IoU {iou:.3f} ({len(cands)} intersecting)")


if __name__ == "__main__":
    main()
