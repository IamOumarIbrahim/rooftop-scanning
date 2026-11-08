"""Quality control of the hand traces: one image per building with the trace and the OSM outline
drawn on the satellite view (thin lines, no fill), so a reader can see whether the trace follows
the roof edge. Also writes a KML with pins for buildings listed in RETRACE, for re-tracing.

Output (contains Google imagery, so it is git-ignored):
    data/reference_traces/_review/Bxx_<id>.png
    data/reference_traces/_to_trace/RETRACE.kml

Usage:  python experiments/review_traces.py [path/to/traces.kml]
"""
import csv
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
from analysis import load_trace_file  # noqa: E402
from export_trace_kml import centroid, kml, placemark  # noqa: E402

OUT = os.path.join(ROOT, "data", "reference_traces", "_review")
QC_FILE = os.path.join(ROOT, "data", "reference_traces", "trace_qc.csv")


def load_qc():
    """trace_qc.csv: id -> (verdict, note). Verdict 'pass' = trace follows the roof edge on the image."""
    if not os.path.exists(QC_FILE):
        return {}
    with open(QC_FILE, encoding="utf-8") as f:
        return {r["id"]: (r["trace_qc"], r["note"]) for r in csv.DictReader(f)}


RETRACE = {k: note for k, (v, note) in load_qc().items() if v != "pass"}


def merc(lat, lon, z):
    w = 256 * 2 ** z
    s = math.sin(math.radians(lat))
    return (lon + 180) / 360 * w, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * w


def main():
    traces = load_trace_file(sys.argv[1] if len(sys.argv) > 1 else
                             os.path.join(ROOT, "data", "reference_traces", "manual_traces.kml"))
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "buildings.csv"), encoding="utf-8")))
    pins = []
    for i, r in enumerate(rows, 1):
        bid = r["id"]
        meta_p = os.path.join(ROOT, "data", "_cache", "imagery", bid + ".json")
        if not os.path.exists(meta_p) or bid not in traces:
            print("skip", bid)
            continue
        m = json.load(open(meta_p, encoding="utf-8"))
        img = plt.imread(os.path.join(ROOT, "data", "_cache", "imagery", bid + ".png"))
        cx, cy = merc(m["center_lat"], m["center_lon"], m["zoom"])
        dpr = m["width_px"] / 1200

        def px(lat, lon):
            x, y = merc(lat, lon, m["zoom"])
            return (x - cx) * dpr + m["width_px"] / 2, (y - cy) * dpr + m["height_px"] / 2
        t = [px(lat, lon) for lon, lat in traces[bid]]
        with open(os.path.join(ROOT, "data", "fixtures", bid + ".json"), encoding="utf-8") as f:
            o = [px(a, b) for a, b in json.load(f)["polygon_coords"]]
        xs, ys = [p[0] for p in t + o], [p[1] for p in t + o]
        sp = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.2
        mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(img)
        ax.plot(*zip(*(t + t[:1])), color="#ff7a00", lw=1.6, label="hand trace")
        ax.plot(*zip(*o), color="#2f6fe0", lw=1.6, label="OSM")
        ax.set_xlim(mx - sp / 2, mx + sp / 2); ax.set_ylim(my + sp / 2, my - sp / 2); ax.axis("off")
        verdict = RETRACE.get(bid, "trace follows the roof edge")  # from trace_qc.csv
        ax.set_title(f"B{i:02d} {r['name']}\n{verdict}", fontsize=11)
        ax.legend(loc="lower right")
        fig.savefig(os.path.join(OUT, f"B{i:02d}_{bid}.png"), dpi=110, bbox_inches="tight")
        plt.close(fig)
        if bid in RETRACE:
            with open(os.path.join(ROOT, "data", "fixtures", bid + ".json"), encoding="utf-8") as f:
                lat, lon, dlat, dlon = centroid(json.load(f)["polygon_coords"])
            pins.append(placemark(bid, f'{r["name"]}: {RETRACE[bid]}', lat, lon, max(dlat, dlon)))
    os.makedirs(os.path.join(ROOT, "data", "reference_traces", "_to_trace"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "reference_traces", "_to_trace", "RETRACE.kml"), "w", encoding="utf-8") as f:
        f.write(kml("\n".join(pins)))
    print(f"wrote {len(rows)} review images to {OUT} and {len(pins)} pins to RETRACE.kml")


if __name__ == "__main__":
    main()
