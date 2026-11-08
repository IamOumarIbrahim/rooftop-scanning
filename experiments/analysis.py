"""Compute every number in the paper from stored inputs.

Inputs (all in the repo, no network):
    data/buildings.csv                  building metadata (no area numbers)
    data/fixtures/<id>.json             OSM footprints (Overpass snapshot)
    data/reference_traces/<id>.kml      manual Google Earth traces (optional)
    data/reference_traces/manual_measurements.csv   screenshot-only manual areas
    data/reference_ms/<id>.geojson      matched Microsoft ML footprints
    solarscan/data/pvgis/*.json         PVGIS yield grids
    results/pvlib_crosscheck.json       independent yield check

Outputs:
    results/validation_dataset.csv      one row per building
    results/results.json                all results
    manuscript/generated/numbers.tex    LaTeX macros used in the paper text
    manuscript/generated/tab_*.tex      LaTeX tables

Usage:  python experiments/analysis.py
"""
import csv
import json
import math
import os
import statistics
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pyproj import Geod  # noqa: E402
from shapely.geometry import Polygon, shape  # noqa: E402

from solarscan.config import DEFAULT_CONFIG as CFG  # noqa: E402
from solarscan.geometry import (  # noqa: E402
    array_azimuth_aligned, calculate_building_axis, calculate_perimeter, calculate_shoelace_area,
    calculate_usable_area, calculate_usable_area_buffered, latlon_to_meters, usable_polygon,
)
from solarscan.sizing import calculate_dc_capacity, calculate_module_count, recommend_inverter_capacity  # noqa: E402
from solarscan.layout import layout_modules  # noqa: E402
from solarscan.yield_estimate import (  # noqa: E402
    calculate_carbon_offset, calculate_discounted_payback, calculate_lcoe, calculate_npv,
    estimate_simple_payback, load_yield_grid, optimal_specific_yield, specific_yield,
)

GEOD = Geod(ellps="WGS84")
MS_IOU_MIN = 0.5          # a Microsoft polygon counts as the same building only above this IoU
CASE_ID = "uos_w5"
SETBACKS = [round(0.25 * i, 2) for i in range(13)]  # 0-3 m


# ---------------------------------------------------------------- inputs
def geodesic_area(lonlat):
    a, p = GEOD.polygon_area_perimeter([c[0] for c in lonlat], [c[1] for c in lonlat])
    return abs(a), p


def read_kml_polygon(path):
    root = ET.parse(path).getroot()
    for el in root.iter():
        if el.tag.endswith("coordinates") and el.text and len(el.text.split()) >= 4:
            pts = [tuple(map(float, t.split(",")[:2])) for t in el.text.split()]
            return pts  # (lon, lat)
    raise ValueError(f"No polygon coordinates in {path}")


def load_trace_file(path):
    """All named polygons in one Google Earth KML file -> {name: [(lon, lat), ...]} (outer ring)."""
    if not os.path.exists(path):
        return {}
    out = {}
    for pm in ET.parse(path).getroot().iter():
        if not pm.tag.endswith("Placemark"):
            continue
        name = next((e.text.strip() for e in pm if e.tag.endswith("name") and e.text), None)
        rings = [e for e in pm.iter() if e.tag.endswith("outerBoundaryIs")]
        if name and rings:
            coords = next(e.text for e in rings[0].iter() if e.tag.endswith("coordinates"))
            out[name] = [tuple(map(float, t.split(",")[:2])) for t in coords.split()]
    return out


TRACES = load_trace_file(os.path.join(ROOT, "data", "reference_traces", "manual_traces.kml"))


def manual_reference(bid, manual_rows):
    kml = os.path.join(ROOT, "data", "reference_traces", f"{bid}.kml")
    if os.path.exists(kml):
        a, p = geodesic_area(read_kml_polygon(kml))
        return a, p, "kml"
    if bid in TRACES:
        a, p = geodesic_area(TRACES[bid])
        return a, p, "kml"
    if bid in manual_rows:
        r = manual_rows[bid]
        return float(r["area_m2"]), float(r["perimeter_m"] or "nan"), "screenshot"
    return None, None, None


def ms_reference(bid):
    path = os.path.join(ROOT, "data", "reference_ms", f"{bid}.geojson")
    if not os.path.exists(path):
        return None, None
    with open(path, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    if not feats:
        return None, None
    g = shape(feats[0]["geometry"])
    g = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda x: x.area)
    return geodesic_area(list(g.exterior.coords))[0], feats[0]["properties"]["iou_with_osm"]


def load_buildings():
    with open(os.path.join(ROOT, "data", "buildings.csv"), encoding="utf-8") as f:
        meta = list(csv.DictReader(f))
    manual_rows = {}
    mm = os.path.join(ROOT, "data", "reference_traces", "manual_measurements.csv")
    if os.path.exists(mm):
        with open(mm, encoding="utf-8") as f:
            manual_rows = {r["id"]: r for r in csv.DictReader(f)}
    qc = {}
    qp = os.path.join(ROOT, "data", "reference_traces", "trace_qc.csv")
    if os.path.exists(qp):  # only traces that follow the roof edge on the image are used as reference
        with open(qp, encoding="utf-8") as f:
            qc = {r["id"]: r["trace_qc"] for r in csv.DictReader(f)}
    status = {}
    sa = os.path.join(ROOT, "data", "reference_traces", "osm_assessment.csv")
    if os.path.exists(sa):
        with open(sa, encoding="utf-8") as f:
            status = {r["id"]: r["osm_status"] for r in csv.DictReader(f)}
    out = []
    for m in meta:
        with open(os.path.join(ROOT, "data", "fixtures", m["id"] + ".json"), encoding="utf-8") as f:
            coords = json.load(f)["polygon_coords"]
        xy = latlon_to_meters(coords)
        area, per = calculate_shoelace_area(xy), calculate_perimeter(xy)
        geo_a, _ = geodesic_area([(c[1], c[0]) for c in coords])
        man_a, man_p, man_src = manual_reference(m["id"], manual_rows)
        man_raw, trace_ok = man_a, qc.get(m["id"], "pass") == "pass"
        if not trace_ok:
            man_a, man_p = None, None
        ms_a, ms_iou = ms_reference(m["id"])
        out.append({**m, "coords": coords, "xy": xy, "n_vertices": len(xy),
                    "osm_area": area, "osm_area_geodesic": geo_a, "osm_perimeter": per,
                    "pa_ratio": per / area, "axis_deg": calculate_building_axis(xy),
                    "manual_area": man_a, "manual_perimeter": man_p, "manual_source": man_src,
                    "manual_area_raw": man_raw, "trace_qc": "pass" if trace_ok else "redo",
                    "ms_area": ms_a, "ms_iou": ms_iou, "osm_status": status.get(m["id"], "unchecked")})
    return out


FAILURE_LABELS = {
    "partial": "Part of building missing",
    "ground_as_roof": "Ground area mapped as roof",
    "courtyard_as_roof": "Open courtyard counted as roof",
    "multi_level": "Roof on several levels",
}
STATUS_SHORT = {"correct": "ok", "partial": "partial", "ground_as_roof": "ground",
                "courtyard_as_roof": "courtyard", "multi_level": "levels", "unchecked": "--"}


# ---------------------------------------------------------------- analysis
def error_stats(pairs):
    """pairs: list of (A_osm, A_ref). Errors are (A_osm - A_ref) / A_ref in %."""
    if not pairs:
        return {"n": 0}
    e = [(o - r) / r * 100 for o, r in pairs]
    ae = [abs(x) for x in e]
    return {"n": len(e), "mape": statistics.mean(ae), "medape": statistics.median(ae),
            "mbe": statistics.mean(e), "min": min(e), "max": max(e),
            "sd": statistics.stdev(e) if len(e) > 1 else 0.0,
            "within5": sum(a <= 5 for a in ae), "within10": sum(a <= 10 for a in ae)}


MODULE_W, MODULE_L = 1.0, 2.0  # m; 2 m^2 x 20 % x 1 kW/m^2 = 400 W per module


def rows_on_roof(xy, setback, gcr, az=180.0, tilt=None):
    tilt = CFG["default_tilt_deg"] if tilt is None else tilt
    return layout_modules(usable_polygon(xy, setback), MODULE_W, MODULE_L, tilt, gcr, az)


def case_study(b, layout):
    s, eta, pack = CFG["setback_m"], CFG["module_efficiency"], CFG["packing_factor"]
    usable = calculate_usable_area_buffered(b["xy"], s)
    az = 180.0 if layout == "south" else array_azimuth_aligned(b["axis_deg"])
    tilt, site = CFG["default_tilt_deg"], "sharjah"
    rows = rows_on_roof(b["xy"], s, pack, az, tilt)
    pdc = rows["n"] * eta * MODULE_W * MODULE_L
    sy = specific_yield(tilt, az, site)
    e = pdc * sy
    c, r = CFG["cost_per_kw"], CFG["rate_aed"]
    fin = dict(cost_per_kw=c, discount_rate=CFG["discount_rate"], lifetime_years=CFG["lifetime_years"],
               om_cost_fraction=CFG["om_cost_fraction"], annual_degradation=CFG["annual_degradation"])
    return {"layout": layout, "usable": usable, "usable_linear": calculate_usable_area(b["osm_area"], b["osm_perimeter"], s),
            "azimuth": az, "tilt": tilt, "pdc": pdc, "pac": recommend_inverter_capacity(pdc, CFG["dc_ac_ratio"]),
            "modules": rows["n"], "modules_rule": usable * pack / (MODULE_W * MODULE_L),
            "pdc_rule": calculate_dc_capacity(usable, eta, pack), "rows": rows,
            "sy": sy, "energy": e, "capex": pdc * c,
            "savings": e * r, "payback": estimate_simple_payback(e, r, c, pdc),
            "disc_payback": calculate_discounted_payback(e, r, pdc, **fin),
            "npv": calculate_npv(e, r, pdc, **fin), "lcoe": calculate_lcoe(e, pdc, **fin),
            "co2": calculate_carbon_offset(e, CFG["grid_co2_kg_per_kwh"])}


def tornado(b):
    """One-at-a-time sensitivity of annual energy and payback for the case-study building."""
    base = case_study(b, "south")
    sy0, e0, pb0 = base["sy"], base["energy"], base["payback"]
    c0, r0 = CFG["cost_per_kw"], CFG["rate_aed"]

    def energy(setback=CFG["setback_m"], pack=CFG["packing_factor"], eta=CFG["module_efficiency"], sy=sy0):
        return rows_on_roof(b["xy"], setback, pack)["n"] * eta * MODULE_W * MODULE_L * sy

    def payback(c=c0, r=r0, sy=sy0):
        return c / (sy * r)

    sy_aligned = specific_yield(CFG["default_tilt_deg"], array_azimuth_aligned(b["axis_deg"]), "sharjah")
    # (input name, value giving the worse result, value giving the better result, worse result, better result)
    rows_e = [
        ("Roof share used", "60%", "80%", energy(pack=0.60), energy(pack=0.80)),
        ("Module efficiency", "18%", "22%", energy(eta=0.18), energy(eta=0.22)),
        ("Edge strip", "2 m", "1 m", energy(setback=2.0), energy(setback=1.0)),
        ("Solar yield", "-5%", "+5%", energy(sy=sy0 * 0.95), energy(sy=sy0 * 1.05)),
        ("Row direction", "along walls", "south", energy(sy=sy_aligned), e0),
    ]
    rows_p = [
        ("Cost (AED/kWp)", "4,000", "2,500", payback(c=4000), payback(c=2500)),
        ("Price (AED/kWh)", "0.29", "0.44", payback(r=0.29), payback(r=0.44)),
        ("Solar yield", "-5%", "+5%", payback(sy=sy0 * 0.95), payback(sy=sy0 * 1.05)),
        ("Row direction", "along walls", "south", payback(sy=sy_aligned), pb0),
    ]

    def pack_rows(rows):
        return [{"name": n, "worse_input": wi, "better_input": bi, "worse": w, "better": bt,
                 "label": f"{n} {wi} / {bi}", "low": w, "high": bt} for n, wi, bi, w, bt in rows]
    return {"energy_base": e0, "payback_base": pb0, "energy": pack_rows(rows_e), "payback": pack_rows(rows_p)}


def row_shading(lat=25.2893, lon=55.4783, day="2026-12-21"):
    """Row-to-row shading on the shortest day: noon sun height, shadow of one row, and the hours without shading.

    A row of L-long modules at tilt t rises L sin t; the next row starts pitch - L cos t behind it. The next row
    is shaded while the sun's profile angle (elevation seen in the north-south plane) is below
    atan(rise / gap). Solar positions from pvlib (NREL SPA)."""
    import numpy as np
    import pandas as pd
    import pvlib
    L, tilt, gcr = MODULE_L, math.radians(CFG["default_tilt_deg"]), CFG["packing_factor"]
    pitch, rise = L / gcr, L * math.sin(tilt)
    gap = pitch - L * math.cos(tilt)
    crit = math.degrees(math.atan(rise / gap))
    t = pd.date_range(f"{day} 05:00", f"{day} 19:00", freq="1min", tz="Asia/Dubai")
    sp = pvlib.solarposition.get_solarposition(t, lat, lon)
    el, az = sp["apparent_elevation"].to_numpy(), sp["azimuth"].to_numpy()
    c = np.cos(np.radians(az - 180))
    prof = np.degrees(np.arctan2(np.tan(np.radians(np.clip(el, 0, 89.9))), c))
    free = (el > 0) & (c > 0) & (prof >= crit)
    noon = float(el.max())
    return {"day": day, "pitch_m": pitch, "gap_m": gap, "rise_m": rise, "critical_profile_deg": crit,
            "noon_elev_deg": noon, "noon_shadow_m": rise / math.tan(math.radians(noon)),
            "free_from": t[free][0].strftime("%H:%M"), "free_to": t[free][-1].strftime("%H:%M")}


def layout_check(bs):
    """Modules that fit in real rows vs the simple packing rule A_u * k / (W * L), per building."""
    out = []
    for b in bs:
        u = usable_polygon(b["xy"], CFG["setback_m"])
        n = rows_on_roof(b["xy"], CFG["setback_m"], CFG["packing_factor"])["n"]
        rule = u.area * CFG["packing_factor"] / (MODULE_W * MODULE_L)
        out.append({"id": b["id"], "usable": u.area, "n_layout": n, "n_rule": rule, "ratio": n / rule if rule else 0})
    r = [x["ratio"] for x in out if x["n_rule"] > 0]
    return {"rows": out, "median": statistics.median(r), "min": min(r), "max": max(r)}


def write_scene(b, case):
    """Geometry of the case-study roof and its module rows, for the Blender render and Fig. 1."""
    s = case["south"]
    u = usable_polygon(b["xy"], CFG["setback_m"])
    u = u if u.geom_type == "Polygon" else max(u.geoms, key=lambda g: g.area)
    scene = {"id": b["id"], "footprint": [list(p) for p in b["xy"]],
             "usable": [list(p) for p in list(u.exterior.coords)[:-1]],
             "modules": [[list(p) for p in m] for m in s["rows"]["modules"]],
             "tilt_deg": s["rows"]["tilt_deg"], "length_m": s["rows"]["length_m"], "width_m": s["rows"]["width_m"],
             "pitch_m": s["rows"]["pitch_m"], "azimuth_deg": s["rows"]["azimuth_deg"],
             "n_modules": s["modules"], "pdc_kwp": s["pdc"], "energy_mwh": s["energy"] / 1000}
    for k in ("south", "aligned"):
        case[k].pop("rows", None)
    with open(os.path.join(ROOT, "results", "scene_w5.json"), "w", encoding="utf-8") as f:
        json.dump(_rounded(scene, 3), f)


def setback_analysis(bs):
    rows = []
    for b in bs:
        exact = [calculate_usable_area_buffered(b["xy"], s) / b["osm_area"] for s in SETBACKS]
        linear = [calculate_usable_area(b["osm_area"], b["osm_perimeter"], s) / b["osm_area"] for s in SETBACKS]
        rows.append({"id": b["id"], "category": b["category"], "area": b["osm_area"], "pa": b["pa_ratio"],
                     "exact": exact, "linear": linear})
    i15 = SETBACKS.index(1.5)
    diff = [abs(r["exact"][i15] - r["linear"][i15]) * 100 for r in rows]
    frac = [r["exact"][i15] * 100 for r in rows]
    return {"setbacks": SETBACKS, "rows": rows, "usable_at_1p5_min": min(frac), "usable_at_1p5_max": max(frac),
            "linear_vs_exact_max_pp": max(diff), "linear_vs_exact_median_pp": statistics.median(diff)}


def orientation_summary(site="sharjah"):
    g = load_yield_grid(site)
    best = optimal_specific_yield(site)
    bt, ba = max(((int(t), int(a)) for t in g["specific_yield"] for a in g["specific_yield"][t]),
                 key=lambda ta: g["specific_yield"][str(ta[0])][str(ta[1])])
    pct = lambda t, a: specific_yield(t, a, site) / best * 100  # noqa: E731
    return {"best": best, "best_tilt": bt, "best_az": ba, "flat_pct": pct(0, 180),
            "s15_pct": pct(15, 180), "e15_pct": pct(15, 90), "w15_pct": pct(15, 270), "n15_pct": pct(15, 0),
            "radiation_db": g.get("radiation_db"), "years": f'{g.get("year_min")}-{g.get("year_max")}',
            "sites": {s: specific_yield(15, 180, s) for s in
                      ("sharjah", "dubai", "abu_dhabi", "ajman", "ras_al_khaimah")}}


# ---------------------------------------------------------------- outputs
def fmt(x, d=0):
    return f"{x:,.{d}f}"


def tex_escape(s):
    return s.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def write_dataset(bs):
    path = os.path.join(ROOT, "results", "validation_dataset.csv")
    cols = ["id", "name", "emirate", "category", "osm_way_id", "n_vertices", "osm_area", "osm_perimeter",
            "pa_ratio", "axis_deg", "manual_area", "manual_area_raw", "trace_qc", "manual_source", "osm_status", "ms_area", "ms_iou"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for b in bs:
            w.writerow([round(b[c], 4) if isinstance(b[c], float) else ("" if b[c] is None else b[c]) for c in cols])


def write_tables(bs, case, gen):
    # Table: benchmark buildings
    L = [r"\begin{table*}[t]", r"\centering",
         r"\caption{Benchmark Buildings: OSM Footprint Area Against the Manual Roof Trace}",
         r"\label{tab:buildings}", r"\footnotesize", r"\setlength{\tabcolsep}{3.5pt}",
         r"\begin{tabular}{llllrrrl}", r"\toprule",
         r"ID & Building & Emirate & Type & OSM area (m$^2$) & Traced area (m$^2$) & Error (\%) & OSM outline \\",
         r"\midrule"]
    for i, b in enumerate(bs, 1):
        man = fmt(b["manual_area"]) if b["manual_area"] else "--"
        err = f'{(b["osm_area"] - b["manual_area"]) / b["manual_area"] * 100:+.1f}' if b["manual_area"] else "--"
        err = err.replace("-", "$-$").replace("+", "$+$")
        status = {"correct": "correct", "partial": "part missing", "ground_as_roof": "ground as roof",
                  "courtyard_as_roof": "courtyard as roof", "multi_level": "several levels"}.get(b["osm_status"], "--")
        if b["trace_qc"] != "pass":
            status = "trace redone"
        row = (f'B{i:02d} & {tex_escape(b["name"])} & {b["emirate"]} & {b["category"]} & {fmt(b["osm_area"])} & '
               f'{man} & {err} & {status} \\\\')
        L.append(row if b["osm_status"] == "correct" else r"\rowcolor{black!8}" + row)
    L += [r"\bottomrule", r"\multicolumn{8}{l}{Error $=(A_{\mathrm{OSM}}-A_{\mathrm{trace}})/A_{\mathrm{trace}}$. "
          r"Grey rows: the OSM outline does not match the building (Table~\ref{tab:failures})"
          + (", or the hand trace failed the image check." if any(b["trace_qc"] != "pass" for b in bs) else ".")
          + r"}\\",
          r"\end{tabular}", r"\end{table*}"]
    open(os.path.join(gen, "tab_buildings.tex"), "w", encoding="utf-8").write("\n".join(L))

    # Table: OSM failure types
    L = [r"\begin{table}[t]", r"\centering", r"\caption{How the OSM Outline Failed}",
         r"\label{tab:failures}", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabular}{lcl}", r"\toprule", r"Failure type & $n$ & Area error (\%) \\", r"\midrule"]
    for key, label in FAILURE_LABELS.items():
        es = [(b["osm_area"] - b["manual_area"]) / b["manual_area"] * 100 for b in bs
              if b["osm_status"] == key and b["manual_area"]]
        if es:
            rng = f"{min(es):+.0f}" if len(es) == 1 else f"{min(es):+.0f} to {max(es):+.0f}"
            L.append(f"{label} & {len(es)} & {rng.replace('-', '$-$').replace('+', '$+$')} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    open(os.path.join(gen, "tab_failures.tex"), "w", encoding="utf-8").write("\n".join(L))



def _rounded(o, nd=6):
    """Round floats so the stored results do not change with tiny platform differences."""
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: _rounded(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_rounded(v, nd) for v in o]
    return o


def _err(b):
    """OSM area error against the manual trace, in %."""
    return (b["osm_area"] - b["manual_area"]) / b["manual_area"] * 100


def macro_name(key):
    return "".join(p.capitalize() for p in key.replace("_", " ").split())


def write_numbers(nums, gen):
    lines = ["% Generated by experiments/analysis.py. Do not edit by hand."]
    for k, v in nums.items():
        v = str(v)
        if v[:1] in "+-" and v[1:2].isdigit():  # typeset sign as a math symbol so it never breaks from the number
            v = f"${v[0]}${v[1:]}"
        lines.append(f"\\newcommand{{\\{macro_name(k)}}}{{{v}}}")
    open(os.path.join(gen, "numbers.tex"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    gen = os.path.join(ROOT, "manuscript", "generated")
    os.makedirs(gen, exist_ok=True)

    bs = load_buildings()
    write_dataset(bs)
    ms_pairs = [(b["osm_area"], b["ms_area"]) for b in bs if b["ms_iou"] is not None and b["ms_iou"] >= MS_IOU_MIN]
    man_pairs = [(b["osm_area"], b["manual_area"]) for b in bs if b["manual_area"]]
    ms_all = error_stats(ms_pairs)
    man_all = error_stats(man_pairs)
    ok = [b for b in bs if b["manual_area"] and b["osm_status"] == "correct"]
    bad = [b for b in bs if b["manual_area"] and b["osm_status"] not in ("correct", "unchecked")]
    man_ok = error_stats([(b["osm_area"], b["manual_area"]) for b in ok])
    # How good is the second reference? Microsoft vs manual trace, same building (IoU with OSM >= threshold)
    ms_vs_man = error_stats([(b["ms_area"], b["manual_area"]) for b in bs if b["manual_area"]
                             and b["ms_iou"] is not None and b["ms_iou"] >= MS_IOU_MIN])
    fail_counts = {k: sum(b["osm_status"] == k for b in bad) for k in FAILURE_LABELS}
    ms_by_cat = {c: error_stats([(b["osm_area"], b["ms_area"]) for b in bs if b["category"] == c
                                 and b["ms_iou"] is not None and b["ms_iou"] >= MS_IOU_MIN])
                 for c in sorted({b["category"] for b in bs})}
    proj_err = max(abs(b["osm_area"] - b["osm_area_geodesic"]) / b["osm_area_geodesic"] * 100 for b in bs)

    w5 = next(b for b in bs if b["id"] == CASE_ID)
    case = {"area": w5["osm_area"], "perimeter": w5["osm_perimeter"], "axis": w5["axis_deg"],
            "n_vertices": w5["n_vertices"], "osm_way_id": w5["osm_way_id"],
            "south": case_study(w5, "south"), "aligned": case_study(w5, "aligned")}
    torn = tornado(w5)
    shade = row_shading()
    sb = setback_analysis(bs)
    lc = layout_check(bs)
    write_scene(w5, case)
    ori = orientation_summary()
    with open(os.path.join(ROOT, "results", "pvlib_crosscheck.json"), encoding="utf-8") as f:
        pvl = json.load(f)

    results = {"n_buildings": len(bs), "ms_iou_min": MS_IOU_MIN, "validation_ms": ms_all,
               "validation_ms_by_category": ms_by_cat, "validation_manual": man_all,
               "validation_manual_osm_correct": man_ok, "ms_vs_manual": ms_vs_man, "osm_failures": fail_counts,
               "projection_max_err_pct": proj_err, "case": case, "tornado": torn, "setback": sb,
               "orientation": ori, "pvlib": pvl, "config": CFG, "layout_check": lc, "row_shading": shade,
               "buildings": [{k: v for k, v in b.items() if k not in ("coords", "xy")} for b in bs]}
    with open(os.path.join(ROOT, "results", "results.json"), "w", encoding="utf-8") as f:
        json.dump(_rounded(results), f, indent=1, default=float)

    s, a = case["south"], case["aligned"]
    jf = next(b for b in bs if b["id"] == "jebel_ali_wh")
    areas = [b["osm_area"] for b in bs]
    na = "n/a"
    nums = {
        "n_buildings": len(bs), "n_emirates": len({b["emirate"] for b in bs}),
        "n_academic": sum(b["category"] == "Academic" for b in bs),
        "n_commercial": sum(b["category"] == "Commercial" for b in bs),
        "n_industrial": sum(b["category"] == "Industrial" for b in bs),
        "ok_max_abs": f'{max(abs(man_ok["min"]), abs(man_ok["max"])):.1f}',
        "area_min": fmt(min(areas)), "area_max": fmt(max(areas)),
        "n_ms_matched": sum(b["ms_iou"] is not None for b in bs), "n_ms_used": ms_all["n"],
        "ms_iou_min": MS_IOU_MIN,
        "ms_mape": f'{ms_all["mape"]:.1f}', "ms_medape": f'{ms_all["medape"]:.1f}',
        "ms_mbe": f'{ms_all["mbe"]:+.1f}', "ms_min": f'{ms_all["min"]:+.1f}', "ms_max": f'{ms_all["max"]:+.1f}',
        "ms_within_ten": ms_all["within10"],
        "n_manual": man_all["n"], "n_trace_redo": sum(b["trace_qc"] != "pass" for b in bs),
        "partial_min": f'{min(abs(_err(b)) for b in bad if b["osm_status"] == "partial"):.0f}',
        "partial_max": f'{max(abs(_err(b)) for b in bad if b["osm_status"] == "partial"):.0f}',
        "man_mape": f'{man_all["mape"]:.1f}' if man_all["n"] else na,
        "man_mbe": f'{man_all["mbe"]:+.1f}' if man_all["n"] else na,
        "man_medape": f'{man_all["medape"]:.1f}' if man_all["n"] else na,
        "man_within_ten": man_all.get("within10", 0),
        "n_osm_ok": man_ok["n"], "n_osm_bad": len(bad), "osm_bad_pct": f'{len(bad) / max(1, man_all["n"]) * 100:.0f}',
        "ok_mape": f'{man_ok["mape"]:.1f}', "ok_medape": f'{man_ok["medape"]:.1f}', "ok_mbe": f'{man_ok["mbe"]:+.1f}',
        "ok_min": f'{man_ok["min"]:+.1f}', "ok_max": f'{man_ok["max"]:+.1f}', "ok_sd": f'{man_ok["sd"]:.1f}',
        "ok_within_five": man_ok["within5"], "ok_within_ten": man_ok["within10"],
        "n_partial": fail_counts["partial"], "n_ground": fail_counts["ground_as_roof"],
        "n_courtyard": fail_counts["courtyard_as_roof"], "n_levels": fail_counts["multi_level"],
        "msman_n": ms_vs_man["n"], "msman_medape": f'{ms_vs_man["medape"]:.1f}', "msman_mape": f'{ms_vs_man["mape"]:.1f}',
        "msman_mbe": f'{ms_vs_man["mbe"]:+.1f}',
        "case_man": fmt(w5["manual_area"]), "case_man_err": f'{(w5["osm_area"] - w5["manual_area"]) / w5["manual_area"] * 100:+.1f}',
        "proj_err": f"{proj_err:.4f}",
        "case_area": fmt(case["area"], 1), "case_perimeter": fmt(case["perimeter"], 1),
        "case_vertices": case["n_vertices"], "case_way": case["osm_way_id"], "case_axis": f'{case["axis"]:.1f}',
        "case_usable": fmt(s["usable"], 1), "case_usable_pct": f'{s["usable"] / case["area"] * 100:.1f}',
        "case_usable_linear": fmt(s["usable_linear"], 1),
        "case_pdc": fmt(s["pdc"], 1), "case_pac": fmt(s["pac"], 1), "case_modules": s["modules"],
        "case_modules_rule": fmt(s["modules_rule"]), "case_pdc_rule": fmt(s["pdc_rule"], 1),
        "case_rule_gap": f'{(1 - s["modules"] / s["modules_rule"]) * 100:.0f}',
        "lc_median": f'{lc["median"] * 100:.0f}', "lc_min": f'{lc["min"] * 100:.0f}', "lc_max": f'{lc["max"] * 100:.0f}',
        "lc_n": len(lc["rows"]), "module_w": f'{CFG["module_efficiency"] * MODULE_W * MODULE_L * 1000:.0f}',
        "row_pitch": f'{2 / CFG["packing_factor"]:.2f}',
        "case_sy": fmt(s["sy"]), "case_energy": fmt(s["energy"] / 1000, 1),
        "case_capex": fmt(s["capex"]), "case_savings": fmt(s["savings"]),
        "case_payback": f'{s["payback"]:.1f}', "case_disc_payback": f'{s["disc_payback"]:.1f}',
        "case_npv": fmt(s["npv"]), "case_lcoe": f'{s["lcoe"]:.3f}', "case_co": fmt(s["co2"]),
        "case_al_az": f'{a["azimuth"]:.0f}', "case_al_sy": fmt(a["sy"]), "case_al_energy": fmt(a["energy"] / 1000, 1),
        "case_al_payback": f'{a["payback"]:.1f}', "case_al_loss": f'{(1 - a["sy"] / s["sy"]) * 100:.1f}',
        "pay_min": f'{min(min(r["low"], r["high"]) for r in torn["payback"]):.1f}',
        "pay_max": f'{max(max(r["low"], r["high"]) for r in torn["payback"]):.1f}',
        "sb_min": f'{sb["usable_at_1p5_min"]:.1f}', "sb_max": f'{sb["usable_at_1p5_max"]:.1f}',
        "sb_lin_max": f'{sb["linear_vs_exact_max_pp"]:.1f}', "sb_lin_med": f'{sb["linear_vs_exact_median_pp"]:.2f}',
        "or_best": fmt(ori["best"]), "or_best_tilt": ori["best_tilt"], "or_best_az": ori["best_az"],
        "or_flat": f'{ori["flat_pct"]:.1f}', "or_south": f'{ori["s15_pct"]:.1f}', "or_east": f'{ori["e15_pct"]:.1f}',
        "or_west": f'{ori["w15_pct"]:.1f}', "or_north": f'{ori["n15_pct"]:.1f}',
        "or_site_min": fmt(min(ori["sites"].values())), "or_site_max": fmt(max(ori["sites"].values())),
        "pvlib_max": f'{pvl["max_abs_diff_pct"]:.1f}', "ghi": fmt(pvl["ghi_kwh_m2"]), "tmax": f'{pvl["t_air_max_c"]:.0f}',
        "jafza_osm_vs_man": f'{(jf["osm_area"] - jf["manual_area"]) / jf["manual_area"] * 100:+.1f}',
        "jafza_osm_vs_ms": f'{(jf["osm_area"] - jf["ms_area"]) / jf["ms_area"] * 100:+.1f}',
        "jafza_ref_gap": f'{(jf["manual_area"] - jf["ms_area"]) / jf["ms_area"] * 100:.1f}',
        "jafza_man": fmt(jf["manual_area"]), "jafza_ms": fmt(jf["ms_area"]), "jafza_osm": fmt(jf["osm_area"]),
        "case_ms_err": f'{(w5["osm_area"] - w5["ms_area"]) / w5["ms_area"] * 100:+.1f}',
        "iou_median": f'{statistics.median([b["ms_iou"] for b in bs if b["ms_iou"] is not None]):.2f}',
        "cfg_cost": fmt(CFG["cost_per_kw"]), "cfg_tariff": f'{CFG["rate_aed"]:.2f}',
        "cfg_pack": f'{CFG["packing_factor"]:.2f}', "cfg_eta": f'{CFG["module_efficiency"] * 100:.0f}',
        "cfg_setback": f'{CFG["setback_m"]:.1f}', "cfg_tilt": f'{CFG["default_tilt_deg"]:.0f}',
        "cfg_dcac": f'{CFG["dc_ac_ratio"]:.1f}', "cfg_deg": f'{CFG["annual_degradation"] * 100:.1f}',
        "cfg_om": f'{CFG["om_cost_fraction"] * 100:.1f}', "cfg_co": f'{CFG["grid_co2_kg_per_kwh"]:.2f}',
        "cfg_disc": f'{CFG["discount_rate"] * 100:.0f}', "cfg_life": f'{CFG["lifetime_years"]}',
        "shade_elev": f'{shade["noon_elev_deg"]:.0f}', "shade_len": f'{shade["noon_shadow_m"]:.2f}',
        "shade_gap": f'{shade["gap_m"]:.2f}', "shade_from": shade["free_from"], "shade_to": shade["free_to"],
    }
    write_numbers(nums, gen)
    write_tables(bs, case, gen)
    print(json.dumps({k: nums[k] for k in nums}, indent=0, ensure_ascii=False))


if __name__ == "__main__":
    main()
