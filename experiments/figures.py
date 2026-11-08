"""Draw every paper figure from stored data, results and renders.

Inputs: results/results.json, results/scene_w5.json, data/fixtures/, the manual traces,
manuscript/figures/render_w5.png (Blender), data/_cache/imagery/ (Google satellite views,
see fetch_imagery.py) and data/_cache/boundaries/ (geoBoundaries, see fetch_boundaries.py).

IEEE figure rules applied: figures drawn at their final width (column 3.5 in, page 7.16 in),
8 pt Times text, axis labels in words with units, and series told apart by line style or
marker shape as well as color, so they also work in grayscale. Map panels are north-up
and carry a scale bar. Imagery credits are printed in the figure.

Usage:  python experiments/figures.py
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Polygon as MplPolygon  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
from shapely.geometry import Polygon, shape  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))
from analysis import TRACES  # noqa: E402
from solarscan.yield_estimate import specific_yield, optimal_specific_yield  # noqa: E402

OUT = os.path.join(ROOT, "manuscript", "figures")
IMG = os.path.join(ROOT, "data", "_cache", "imagery")
BND = os.path.join(ROOT, "data", "_cache", "boundaries")
COL, PAGE = 3.5, 7.16
PT = 8

OSM, TRACE, GOOD, BAD = "#1f4e9a", "#e07b2a", "#1f4e9a", "#e07b2a"
INK, INK2, MUTED, GRID = "#111111", "#444444", "#8c8c8c", "#e6e6e6"
STRIP, USABLE, MODULE = "#f2c9a0", "#e9e9e9", "#14285a"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": PT, "axes.labelsize": PT, "xtick.labelsize": PT, "ytick.labelsize": PT, "legend.fontsize": PT,
    "axes.titlesize": PT, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.linewidth": 0.6, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.dpi": 300, "savefig.bbox": None, "figure.constrained_layout.use": True, "legend.frameon": False,
    "hatch.color": BAD, "hatch.linewidth": 0.6,
})
KEEP = ("fig_hero", "fig_map", "fig_failures", "fig_validation", "fig_orientation", "fig_tornado", "render_w5",
        "fig_gui", "fig_report", "render_rows")


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"), metadata={"CreationDate": None})
    fig.savefig(os.path.join(OUT, name + ".png"))
    plt.close(fig)
    print("wrote", name)


def minus(s):
    return s.replace("-", "−")


def bare(ax):
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)


# ---------------------------------------------------------------- imagery helpers
def merc(lat, lon, z):
    w = 256 * 2 ** z
    s = math.sin(math.radians(lat))
    return (lon + 180) / 360 * w, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * w


def imagery(bid):
    """Cached satellite view and a function mapping (lat, lon) to image pixels."""
    with open(os.path.join(IMG, bid + ".json"), encoding="utf-8") as f:
        m = json.load(f)
    img = plt.imread(os.path.join(IMG, bid + ".png"))
    cx, cy = merc(m["center_lat"], m["center_lon"], m["zoom"])
    dpr = m["width_px"] / 1200

    def px(lat, lon):
        x, y = merc(lat, lon, m["zoom"])
        return (x - cx) * dpr + m["width_px"] / 2, (y - cy) * dpr + m["height_px"] / 2
    return img, m, px


def osm_latlon(bid):
    with open(os.path.join(ROOT, "data", "fixtures", bid + ".json"), encoding="utf-8") as f:
        return json.load(f)["polygon_coords"]


def scale_bar(ax, meters, units_per_m, x0, y0, color=INK, invert_y=False):
    L = meters * units_per_m
    ax.plot([x0, x0 + L], [y0, y0], color=color, lw=2.2, solid_capstyle="butt")
    ax.text(x0 + L / 2, y0 + (-1 if invert_y else 1) * L * 0.12, f"{meters:g} m", ha="center",
            va="bottom", color=color)


def north_arrow(ax, x, y, size, color=INK, invert_y=False):
    d = -size if invert_y else size
    ax.annotate("", xy=(x, y + d), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2))
    ax.text(x, y + d * 1.25, "N", ha="center", va="center", color=color, weight="bold")


HALO = [pe.withStroke(linewidth=2.6, foreground="white")]
TEXT_HALO = [pe.withStroke(linewidth=1.5, foreground="black")]
OSM_LINE, TRACE_LINE, TRACE_FILL = "#2f6fe0", "#ff8a1f", (1.0, 0.55, 0.12, 0.38)


def image_panel(ax, bid, title, margin=0.35, bar=None, fill_trace=True):
    """Satellite image. Hand trace = filled roof area (orange); OSM footprint = outline (blue, white halo)."""
    img, meta, px = imagery(bid)
    o = [px(a, b) for a, b in osm_latlon(bid)]
    t = [px(lat, lon) for lon, lat in TRACES[bid]]
    xs, ys = [p[0] for p in o + t], [p[1] for p in o + t]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) * (1 + 2 * margin)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    ax.imshow(img, interpolation="lanczos")
    ax.add_patch(MplPolygon(t, closed=True, fc=TRACE_FILL if fill_trace else "none", ec=TRACE_LINE,
                            lw=1.0 if fill_trace else 1.6, ls=(0, (3, 1.5))))
    ax.add_patch(MplPolygon(o, closed=True, fill=False, ec=OSM_LINE, lw=1.4, path_effects=HALO))
    ax.set_xlim(cx - span / 2, cx + span / 2); ax.set_ylim(cy + span / 2, cy - span / 2)
    bare(ax)
    ax.set_title(title, pad=2)
    ppm = 1 / meta["m_per_px"]
    bar = bar or max(v for v in (5, 10, 20, 50, 100) if v * ppm <= span * 0.3)
    x0, y0 = cx - span * 0.44, cy + span * 0.42
    ax.plot([x0, x0 + bar * ppm], [y0, y0], color="white", lw=2.4, solid_capstyle="butt",
            path_effects=[pe.withStroke(linewidth=3.6, foreground="black")])
    ax.text(x0 + bar * ppm / 2, y0 - span * 0.08, f"{bar:g} m", ha="center", va="bottom", color="white",
            path_effects=TEXT_HALO)
    return meta


# ---------------------------------------------------------------- Fig. 1: what the tool does on one roof
def fig_hero(res):
    with open(os.path.join(ROOT, "results", "scene_w5.json"), encoding="utf-8") as f:
        sc = json.load(f)
    s = res["case"]["south"]
    fig, axes = plt.subplots(1, 4, figsize=(PAGE, 2.35), gridspec_kw={"width_ratios": [1, 1, 1.1, 1.1]})

    meta = image_panel(axes[0], "uos_w5", "(a) Satellite image", margin=0.12,
                       fill_trace=False)  # keep the dome and roof equipment visible
    xl, yl = axes[0].get_xlim(), axes[0].get_ylim()
    north_arrow(axes[0], xl[1] - (xl[1] - xl[0]) * 0.08, yl[0] - (yl[0] - yl[1]) * 0.25,
                (yl[0] - yl[1]) * 0.1, color="white", invert_y=True)

    ax = axes[1]
    fp = Polygon(sc["footprint"])
    ax.add_patch(MplPolygon(sc["footprint"], closed=True, fc=STRIP, ec=OSM, lw=1.2))
    ax.add_patch(MplPolygon(sc["usable"], closed=True, fc=USABLE, ec="none"))
    ax.add_collection(PolyCollection(sc["modules"], facecolors=MODULE, edgecolors="none"))
    minx, miny, maxx, maxy = fp.bounds
    span = max(maxx - minx, maxy - miny) * 1.08
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    ax.set_xlim(cx - span / 2, cx + span / 2); ax.set_ylim(cy - span / 2, cy + span / 2)
    ax.set_aspect("equal"); bare(ax)
    ax.set_title("(b) Usable roof and modules", pad=2)
    scale_bar(ax, 10, 1, cx - span * 0.46, cy - span * 0.47)
    north_arrow(ax, cx + span * 0.42, cy + span * 0.28, span * 0.1)
    ax.text(cx + span * 0.52, cy - span * 0.52,
            f'{s["modules"]} modules\n{s["pdc"]:,.0f} kWp\n{s["energy"] / 1000:,.0f} MWh/yr',
            ha="right", va="bottom", linespacing=1.1, fontsize=6.5)

    ax = axes[2]
    r = plt.imread(os.path.join(OUT, "render_w5.png"))
    rows, cols = np.where(r[..., 3] > 0.02)  # crop to the building and its shadow
    pad = 20
    r = r[max(0, rows.min() - pad):rows.max() + pad, max(0, cols.min() - pad):cols.max() + pad]
    ax.imshow(r); bare(ax)
    ax.set_title("(c) 3D view of (b)", pad=2)

    rows_panel(axes[3], res["row_shading"])

    fig.legend(handles=[Line2D([], [], color=OSM_LINE, lw=1.4, path_effects=HALO, label="OSM footprint"),
                        Line2D([], [], color=TRACE_LINE, lw=1.6, ls=(0, (3, 1.5)), label="Roof, hand trace"),
                        Patch(fc=STRIP, ec=OSM, lw=0.8, label=f'{res["config"]["setback_m"]:g} m edge strip'),
                        Patch(fc=USABLE, label="Usable roof"),
                        Patch(fc=MODULE, label=f'Module, 1 m × 2 m, {res["config"]["default_tilt_deg"]:g}° to south')],
               loc="outside lower center", ncol=5, handlelength=1.6, columnspacing=1.0)
    credit = meta["attribution"].replace("(c)", "©").split(", Map data")[0].replace("Imagery ©2026 ", "")
    fig.text(0.005, 0.005, f"(a) Imagery ©2026 Google, {credit}. (c) Building height is illustrative.", fontsize=6, color=INK2)
    save(fig, "fig_hero")


def rows_panel(ax, sh):
    """(d): rows at the default spacing in the noon sun of the shortest day (Blender), with the gap and the shadow."""
    img = plt.imread(os.path.join(OUT, "render_rows.png"))
    with open(os.path.join(ROOT, "results", "render_rows_points.json"), encoding="utf-8") as f:
        P = json.load(f)["points"]
    ax.imshow(img)
    ax.set_xlim(img.shape[1] * 0.28, img.shape[1] * 0.99); ax.set_ylim(img.shape[0] * 0.82, img.shape[0] * 0.22)
    bare(ax)
    ax.set_title("(d) Noon, 21 December", pad=2)
    sun = "#d99a00"
    (xs, ys), (xt, yt), (xe, ye) = P["sun_from"], P["row1_top"], P["shadow_end"]
    ax.plot([xs, xt], [ys, yt], color=sun, lw=1.3, solid_capstyle="round")
    ax.annotate("", xy=(xe, ye), xytext=(xt, yt), arrowprops=dict(arrowstyle="-|>", color=sun, lw=1.3, ls=(0, (3, 2))))
    ax.text(xs - 8, ys - 10, f"sun {sh['noon_elev_deg']:.0f}°", color=INK, ha="right", va="bottom", fontsize=6.5,
            path_effects=HALO)
    for a, b, txt, off, col in (("gap_a", "shadow_end", f"shadow {sh['noon_shadow_m']:.2f} m", 35, "#b85c00"),
                                ("gap_a", "gap_b", f"gap {sh['gap_m']:.2f} m", 140, OSM)):
        (xa, ya), (xb, yb) = P[a], P[b]
        ax.annotate("", xy=(xb, yb + off), xytext=(xa, ya + off),
                    arrowprops=dict(arrowstyle="|-|", color=col, lw=0.9, shrinkA=0, shrinkB=0, mutation_scale=2.5))
        ax.text(xb + 14, yb + off, txt, color=col, ha="left", va="center", fontsize=6.5, path_effects=HALO)


# ---------------------------------------------------------------- Fig. 2: where the buildings are
def fig_map(res):
    def draw(path, fc, ec, lw, ax):
        with open(path, encoding="utf-8") as f:
            for feat in json.load(f)["features"]:
                g = shape(feat["geometry"])
                for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
                    ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw))
                yield feat["properties"].get("shapeName"), g

    fig, ax = plt.subplots(figsize=(COL, 2.55))
    ax.set_facecolor("#dbe9f5")
    for c in ("omn", "sau", "qat"):
        list(draw(os.path.join(BND, f"{c}_adm0.geojson"), "#efede8", "#b9b5ac", 0.4, ax))
    names = list(draw(os.path.join(BND, "are_adm1.geojson"), "#fbfaf7", "#8c877c", 0.5, ax))
    label_at = {"Abu Dhabi": (54.80, 24.25), "Dubai": (55.32, 24.86), "Sharjah": (55.80, 25.05),
                "Ras al-Khaimah": (56.02, 25.55), "Ajman": (55.25, 25.52)}
    for name, _ in names:
        if name in label_at:
            ax.text(*label_at[name], name.replace("Ras al-Khaimah", "Ras Al Khaimah"), ha="center", va="center",
                    color=INK2, style="italic")
    for b in res["buildings"]:
        c = osm_latlon(b["id"])
        lat, lon = sum(p[0] for p in c) / len(c), sum(p[1] for p in c) / len(c)
        ok = b["osm_status"] == "correct"
        ax.scatter(lon, lat, s=22, marker="o" if ok else "D", fc=GOOD if ok else "white",
                   ec=GOOD if ok else BAD, lw=1.1, zorder=3)
    ax.set_xlim(54.0, 56.4); ax.set_ylim(23.95, 26.05)
    ax.set_aspect(1 / math.cos(math.radians(25)))
    bare(ax)
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color(MUTED)
    km = 1 / (111.32 * math.cos(math.radians(25)))  # degrees of longitude per km
    ax.plot([54.1, 54.1 + 50 * km], [24.08, 24.08], color=INK, lw=2.2, solid_capstyle="butt")
    ax.text(54.1 + 25 * km, 24.12, "50 km", ha="center", va="bottom")
    north_arrow(ax, 54.15, 25.75, 0.15)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", mfc=GOOD, mec=GOOD, ms=5, label="OSM outline correct"),
                       Line2D([], [], marker="D", ls="", mfc="white", mec=BAD, mew=1.1, ms=5, label="OSM outline wrong")],
              loc="lower right", frameon=True, facecolor="white", edgecolor=MUTED, framealpha=1)
    fig.text(0.01, 0.005, "Boundaries: geoBoundaries (OpenStreetMap, ODbL)", fontsize=6, color=INK2)
    save(fig, "fig_map")


# ---------------------------------------------------------------- Fig. 3: how OSM fails, on real imagery
def fig_failures(res):
    by_id = {b["id"]: b for b in res["buildings"]}
    label = {b["id"]: f"B{i:02d}" for i, b in enumerate(res["buildings"], 1)}
    # (id, title, margin): a larger margin for the small annex so the reader sees what kind of building it is
    # Only buildings whose hand trace passed the image check (trace_qc.csv) are shown.
    cases = [("ad_mussafah_wh1", "(a) Correct", 0.15), ("dubai_ondemand_auto", "(b) Part missing", 0.10),
             ("ajman_public_market", "(c) Ground as roof", 0.10), ("ajman_empost_hub", "(d) Courtyard", 0.10),
             ("uos_m13", "(e) Roof levels", 0.6)]
    cases = [c for c in cases if by_id[c[0]]["manual_area"]]
    fig, axes = plt.subplots(1, len(cases), figsize=(PAGE, 2.05))
    credits = set()
    for ax, (bid, title, margin) in zip(axes, cases):
        b = by_id[bid]
        err = (b["osm_area"] - b["manual_area"]) / b["manual_area"] * 100
        e_txt = f"{err:+.1f}" if abs(err) < 10 else f"{err:+.0f}"  # one decimal for small errors (+0.5, not +0)
        meta = image_panel(ax, bid, f"{title}, {label[bid]}\nOSM area {minus(e_txt)}%", margin=margin)
        credits.add(meta["attribution"].replace("(c)", "©").split(", Map data")[0])
    fig.legend(handles=[Line2D([], [], color=OSM_LINE, lw=1.4, path_effects=HALO, label="OSM footprint"),
                        Patch(fc=TRACE_FILL, ec=TRACE_LINE, lw=1.0, ls=(0, (3, 1.5)),
                              label="Roof, traced by hand on the image")],
               loc="outside lower center", ncol=2)
    longest = max(credits, key=len).replace("Imagery ©2026 ", "")
    fig.text(0.005, 0.005, f"Imagery ©2026 Google, {longest}", fontsize=6, color=INK2)
    save(fig, "fig_failures")


# ---------------------------------------------------------------- Fig. 4
def fig_validation(res):
    rows = []
    for i, b in enumerate(res["buildings"], 1):
        if b["manual_area"]:
            rows.append((f"B{i:02d}", (b["osm_area"] - b["manual_area"]) / b["manual_area"] * 100, b["osm_status"]))
    rows.sort(key=lambda r: r[1])
    lim = 40
    fig, ax = plt.subplots(figsize=(COL, 3.1))
    ax.axvspan(-10, 10, color="#f1f1f1", lw=0, zorder=0)
    ax.axvline(0, color=INK2, lw=0.6)
    for y, (lab, e, st) in enumerate(rows):
        ok = st == "correct"
        clipped = abs(e) > lim
        x = float(np.clip(e, -lim + 1.5, lim - 1.5))
        ax.scatter(x, y, s=26, zorder=3, lw=1.1,
                   marker=(">" if e > 0 else "<") if clipped else ("o" if ok else "D"),
                   fc=GOOD if ok else "white", ec=GOOD if ok else BAD)
        if clipped:
            ax.text(x - (3 if e > 0 else -3), y, minus(f"{e:+.0f}%"), ha="right" if e > 0 else "left", va="center",
                    color=INK2)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows])
    ax.set_ylabel("Building")
    ax.set_xlabel("Area error of OSM footprint (%)")
    ax.set_xlim(-lim, lim); ax.set_ylim(-0.8, len(rows) - 0.2); ax.grid(axis="y", lw=0)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", mfc=GOOD, mec=GOOD, ms=5, label="OSM outline correct"),
                       Line2D([], [], marker="D", ls="", mfc="white", mec=BAD, mew=1.1, ms=5, label="OSM outline wrong")],
              loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    save(fig, "fig_validation")


# ---------------------------------------------------------------- Fig. 5
def fig_orientation(res):
    best = optimal_specific_yield("sharjah")
    az = np.arange(0, 361, 5)
    styles = [(0, "0° (flat)", ":", MUTED, 1.4), (15, "15° (default)", "-", OSM, 1.6), (30, "30°", (0, (5, 2)), TRACE, 1.4)]
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    for tilt, label, ls, col, lw in styles:
        ax.plot(az, [specific_yield(tilt, float(a), "sharjah") / best * 100 for a in az],
                ls=ls, color=col, lw=lw, label=f"Tilt {label}")
    ax.set_xticks([0, 90, 180, 270, 360]); ax.set_xticklabels(["N", "E", "S", "W", "N"])
    ax.set_xlim(0, 360); ax.set_ylim(60, 102)
    ax.set_xlabel("Direction the modules face")
    ax.set_ylabel("Energy yield, share of best (%)")
    ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, 1.0), handlelength=2.2, columnspacing=0.9)
    save(fig, "fig_orientation")


# ---------------------------------------------------------------- Fig. 6
def fig_tornado(res):
    """One line per input: the result at its worse value (orange) and better value (blue), with the input
    values written at the ends. The dashed line is the default for W5."""
    t = res["tornado"]
    fig, axes = plt.subplots(2, 1, figsize=(COL, 2.95), gridspec_kw={"height_ratios": [5, 4]})
    panels = ((axes[0], "energy", t["energy_base"] / 1e3, 1e-3, "Yearly energy (MWh)",
               "(a) Energy, more is better (dashed: W5 default, {:.0f} MWh)"),
              (axes[1], "payback", t["payback_base"], 1, "Payback (years)",
               "(b) Payback, shorter is better (dashed: W5 default, {:.1f} years)"))
    for ax, key, b, scale, xlabel, title in panels:
        rows = sorted(t[key], key=lambda r: abs(r["better"] - r["worse"]))  # biggest effect on top
        lo_all = min(min(r["worse"], r["better"]) for r in rows) * scale
        hi_all = max(max(r["worse"], r["better"]) for r in rows) * scale
        pad = (hi_all - lo_all) * 0.24
        ax.set_xlim(lo_all - pad, hi_all + pad)
        ax.axvline(b, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=1)
        for y, r in enumerate(rows):
            w, g = r["worse"] * scale, r["better"] * scale
            if abs(g - w) < (hi_all - lo_all) * 0.03:  # no visible effect: say so instead of two overlapping dots
                ax.scatter([b], [y], s=14, color=MUTED, zorder=3)
                change = abs(r["better"] - r["worse"]) / max(r["better"], r["worse"]) * 100
                ax.annotate(f"{r['worse_input']} or {r['better_input']}: {change:.1f}% change", (b, y),
                            xytext=(5, 0), textcoords="offset points", va="center", ha="left", color=INK2, fontsize=7)
                continue
            ax.plot([w, g], [y, y], color="#c9c9c9", lw=2.2, solid_capstyle="round", zorder=2)
            ax.scatter([w], [y], s=22, color=BAD, zorder=3)
            ax.scatter([g], [y], s=22, color=GOOD, zorder=3)
            for x, txt, other in ((w, r["worse_input"], g), (g, r["better_input"], w)):
                right = x > other
                ax.annotate(minus(txt), (x, y), xytext=(5 if right else -5, 0), textcoords="offset points",
                            va="center", ha="left" if right else "right", fontsize=7, color=INK2)
        ax.set_yticks(range(len(rows))); ax.set_yticklabels([r["name"] for r in rows])
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="y", lw=0)
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_xlabel(xlabel)
        ax.set_title(title.format(b), loc="right", fontsize=7)
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=GOOD, ms=4.5, label="better value"),
                        Line2D([], [], marker="o", ls="", color=BAD, ms=4.5, label="worse value")],
               loc="outside lower center", ncol=2)
    save(fig, "fig_tornado")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):  # remove figures that are no longer drawn
        if f.startswith("fig_") and f.rsplit(".", 1)[0] not in KEEP:
            os.remove(os.path.join(OUT, f))
    with open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8") as f:
        res = json.load(f)
    # Figures with Google imagery or downloaded boundaries need local caches (not in git).
    # Without them, keep the committed versions and redraw the rest.
    have_img = os.path.isdir(IMG) and os.path.exists(os.path.join(OUT, "render_w5.png"))
    if have_img:
        fig_hero(res); fig_failures(res)
    else:
        print("No imagery cache: keeping committed fig_hero and fig_failures (run fetch_imagery.py to redraw)")
    if os.path.isdir(BND):
        fig_map(res)
    fig_validation(res); fig_orientation(res); fig_tornado(res)


if __name__ == "__main__":
    main()
