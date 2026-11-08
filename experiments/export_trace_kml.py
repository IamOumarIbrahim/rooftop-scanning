"""Export one KML per benchmark building for blind manual tracing in Google Earth Pro.

Each KML holds only a pin and a camera view. It does NOT show the OSM outline,
so the manual trace stays independent of the OSM footprint it is compared with.

Usage:
    python experiments/export_trace_kml.py
Output:
    data/reference_traces/_to_trace/<id>.kml
    data/reference_traces/_to_trace/ALL_BUILDINGS.kml
"""
import csv
import json
import os
from xml.sax.saxutils import escape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "reference_traces", "_to_trace")


def centroid(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return sum(lats) / len(lats), sum(lons) / len(lons), max(lats) - min(lats), max(lons) - min(lons)


def placemark(bid, name, lat, lon, span_deg):
    rng = max(150.0, span_deg * 111_000 * 2.5)  # camera distance in metres
    return f"""  <Placemark>
    <name>{escape(bid)}</name>
    <description>{escape(name)}. Trace the outer roof edge (parapet). Save as {escape(bid)}.kml</description>
    <LookAt><longitude>{lon:.7f}</longitude><latitude>{lat:.7f}</latitude><altitude>0</altitude>
      <heading>0</heading><tilt>0</tilt><range>{rng:.0f}</range><altitudeMode>relativeToGround</altitudeMode></LookAt>
    <Point><coordinates>{lon:.7f},{lat:.7f},0</coordinates></Point>
  </Placemark>"""


def kml(body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n'
            f"<Document>\n{body}\n</Document>\n</kml>\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(ROOT, "data", "buildings.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    marks = []
    for r in rows:
        with open(os.path.join(ROOT, "data", "fixtures", r["id"] + ".json"), encoding="utf-8") as f:
            fx = json.load(f)
        lat, lon, dlat, dlon = centroid(fx["polygon_coords"])
        pm = placemark(r["id"], r["name"], lat, lon, max(dlat, dlon))
        marks.append(pm)
        with open(os.path.join(OUT, r["id"] + ".kml"), "w", encoding="utf-8") as f:
            f.write(kml(pm))
    with open(os.path.join(OUT, "ALL_BUILDINGS.kml"), "w", encoding="utf-8") as f:
        f.write(kml("\n".join(marks)))
    print(f"Wrote {len(rows)} KML files to {OUT}")


if __name__ == "__main__":
    main()
