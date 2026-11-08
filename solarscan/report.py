"""
One-page screening report for one building, as PDF (A4) and as self-contained HTML.

Both formats show the same content, built once by build_report_content():
  1. header: building, coordinates, OSM way, date, tool version
  2. four key numbers: system size, yearly energy, investment, payback
  3. roof plan with the modules that fit, and a bar showing where the roof area goes
  4. the system assumed (modules, mounting, rows, inverter, grid, solar data, losses)
  5. money: investment, savings, payback, NPV, LCOE, CO2
  6. payback for other costs and electricity prices (heat map)
  7. limits, and the data credits that the OpenStreetMap licence (ODbL) requires

Values are rounded to what a screening estimate can support.
"""

import base64
import datetime
import html
import io
import logging
import math
import os
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402

from solarscan.yield_estimate import (  # noqa: E402
    calculate_carbon_offset, calculate_lcoe, calculate_npv, calculate_specific_yield,
)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

INK, INK2, LINE, ACCENT = "#14171c", "#59606b", "#d9dee6", "#1f4e9a"
STRIP, USABLE, MODULE = "#f2c9a0", "#e4e6ea", "#14285a"
# Payback heat map: one hue, darker = shorter payback (better)
HEAT = ["#0b2e66", "#1f4e9a", "#4f7cc0", "#8fb0dd", "#c9d8ee", "#eef3fa"]
CREDITS = ("Map data © OpenStreetMap contributors (ODbL). Solar data: PVGIS © European Union, 2001–2026. "
           "Screening estimate, not a design.")
ASPECT = 1.22  # height / width of the roof figure
SYSTEM_LOSS_PCT = 14  # PVGIS default used for the stored yield grids


def _fmt(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}"


def _heat(v: float, lo: float, hi: float) -> Tuple[str, str]:
    """Background and text color for a payback value (shorter = darker)."""
    if not math.isfinite(v):
        return "#ffffff", INK2
    f = 0.0 if hi <= lo else (v - lo) / (hi - lo)
    bg = HEAT[min(len(HEAT) - 1, int(f * len(HEAT)))]
    return bg, ("#ffffff" if HEAT.index(bg) < 3 else INK)


# ---------------------------------------------------------------- content
def build_report_content(d: Dict[str, Any]) -> Dict[str, Any]:
    """Turns scan results into the rounded values and tables shown in both report formats."""
    kwp = d.get("dc_capacity_kw", 0.0)
    kwh = d.get("annual_kwh", 0.0)
    cost = d.get("cost_per_kw", 3000.0)
    tariff = d.get("rate_aed", 0.38)
    sy = calculate_specific_yield(kwh, kwp)
    capex = kwp * cost
    fin = dict(cost_per_kw=cost, discount_rate=d.get("discount_rate", 0.05),
               lifetime_years=int(d.get("lifetime_years", 25)), om_cost_fraction=d.get("om_cost_fraction", 0.015),
               annual_degradation=d.get("annual_degradation", 0.005))
    npv = calculate_npv(kwh, tariff, kwp, **fin) if kwp > 0 else 0.0
    lcoe = calculate_lcoe(kwh, kwp, **fin) if kwp > 0 else float("inf")
    co2_f = d.get("grid_co2_kg_per_kwh", 0.42)
    co2 = calculate_carbon_offset(kwh, co2_f)
    payback = d.get("payback_years", float("inf"))
    n_mod = d.get("n_modules")
    mod_w = d.get("module_w", d.get("module_efficiency", 0.2) * 2000)
    w_m, l_m = d.get("module_width_m", 1.0), d.get("module_length_m", 2.0)
    tilt = d.get("tilt_deg", 15.0)
    gcr = d.get("packing_factor", 0.70)
    pitch = d.get("row_pitch_m") or l_m / gcr
    az = d.get("azimuth_deg", 180.0)
    facing = "south" if abs(az - 180.0) < 1 else f"azimuth {az:.0f}°"
    site = str(d.get("pvgis_site", "")).replace("_", " ").title() or "nearest site"
    ac = d.get("ac_capacity_kw") or kwp / d.get("dc_ac_ratio", 1.2)
    pb_txt = f"{payback:.1f} years" if math.isfinite(payback) else "none"

    key = [
        ("System size", f"{_fmt(kwp)} kWp", f"{_fmt(n_mod)} modules × {mod_w:.0f} W" if n_mod is not None else ""),
        ("Energy per year", f"{_fmt(kwh / 1000)} MWh", f"{_fmt(sy)} kWh per kWp"),
        ("Investment", f"{_fmt(round(capex, -3))} AED", f"saves {_fmt(round(tariff * kwh, -2))} AED per year"),
        ("Payback", pb_txt, f"{_fmt(cost)} AED/kWp | {tariff:.2f} AED/kWh"),
    ]
    system = [
        ("Modules", f"{_fmt(n_mod) if n_mod is not None else '–'} × {mod_w:.0f} W, crystalline Si, "
                    f"{w_m:g} × {l_m:g} m, {d.get('module_efficiency', 0.2):.0%} efficient"),
        ("Mounting", f"fixed racks, {tilt:g}° tilt, facing {facing}"),
        ("Rows", f"{pitch:.2f} m apart ({gcr:.0%} of the roof covered)"),
        ("Edge strip", f"{d.get('setback_m', 1.5):g} m kept clear at the roof edge"),
        ("Inverter", f"{_fmt(ac)} kW ac (dc/ac {d.get('dc_ac_ratio', kwp / ac if ac else 1.2):.1f})"),
        ("Grid", "connected, no battery; all energy used in the building"),
        ("Solar data", f"PVGIS 5.3, {site}: {_fmt(sy)} kWh/kWp per year"),
        ("Losses", f"{SYSTEM_LOSS_PCT}% (cables, inverter, dirt)"),
    ]
    money = [
        ("Investment", f"{_fmt(round(capex, -3))} AED", f"{_fmt(cost)} AED/kWp"),
        ("Savings, year 1", f"{_fmt(round(tariff * kwh, -2))} AED", f"{tariff:.2f} AED/kWh"),
        ("Simple payback", pb_txt, "investment / yearly savings"),
        ("Net present value", f"{_fmt(round(npv, -3))} AED",
         f"{fin['lifetime_years']} years, {fin['discount_rate']:.0%} discount, "
         f"{fin['annual_degradation']:.1%}/yr ageing, {fin['om_cost_fraction']:.1%}/yr O&M"),
        ("Cost of energy (LCOE)", f"{lcoe:.2f} AED/kWh" if math.isfinite(lcoe) else "–", "over the lifetime"),
        ("CO₂ avoided", f"{_fmt(co2)} t per year", f"{co2_f:.2f} kg per kWh of grid power"),
    ]
    # Roof use: footprint = edge strip + gaps between rows + modules (seen from above)
    raw, usable = d.get("raw_area", 0.0), d.get("usable_area", 0.0)
    mods = (n_mod or 0) * w_m * l_m * math.cos(math.radians(tilt))
    roof_use = [("Modules (seen from above)", mods, MODULE), ("Gaps between rows", max(usable - mods, 0.0), USABLE),
                ("Edge strip", max(raw - usable, 0.0), STRIP)]
    costs = (cost - 500.0, cost, cost + 500.0, cost + 1000.0)
    tariffs = (round(tariff - 0.09, 2), round(tariff - 0.04, 2), tariff, round(tariff + 0.06, 2))
    grid = [[(c / (sy * r)) if sy > 0 and r > 0 else float("inf") for r in tariffs] for c in costs]
    limits = [
        ("Outline", "from OpenStreetMap. Compare it with a satellite image: parts can be missing, "
                    "or open ground and courtyards included."),
        ("Not modelled", "roof equipment, shade from taller buildings, roof strength. "
                         "The real system is usually smaller."),
        ("Cost and price", "are defaults. Replace them with quotes and your own bill (see the table)."),
    ]
    return {"key": key, "system": system, "money": money, "roof_use": roof_use, "raw_area": raw,
            "grid": grid, "costs": costs, "tariffs": tariffs, "base": (1, 2), "limits": limits,
            "lat": d.get("lat"), "lon": d.get("lon"), "address": str(d.get("address", "")),
            "way": d.get("osm_way_id"), "date": d.get("report_date") or datetime.date.today().isoformat(),
            "version": d.get("version", ""), "emirate": d.get("emirate"), "utility": d.get("utility")}


# ---------------------------------------------------------------- figure
def roof_plan_png(d: Dict[str, Any], path_or_buffer, width_in: float = 3.9, dpi: int = 220) -> None:
    """Roof plan (north up, scale bar) and below it a bar showing where the roof area goes."""
    fp = d.get("meter_coords") or []
    if len(fp) < 3:
        return
    c = build_report_content(d)
    fig = plt.figure(figsize=(width_in, width_in * ASPECT), dpi=dpi)
    ax = fig.add_axes([0.0, 0.27, 1.0, 0.73])
    bx = fig.add_axes([0.03, 0.165, 0.94, 0.045])
    ax.add_patch(MplPolygon(fp, closed=True, fc=STRIP, ec=ACCENT, lw=1.2))
    for ring in d.get("usable_rings") or []:
        ax.add_patch(MplPolygon(ring, closed=True, fc=USABLE, ec="none"))
    if d.get("modules"):
        ax.add_collection(PolyCollection(d["modules"], facecolors=MODULE, edgecolors="none"))
    xs, ys = [p[0] for p in fp], [p[1] for p in fp]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.1
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    ax.set_xlim(cx - span / 2, cx + span / 2); ax.set_ylim(cy - span / 2, cy + span / 2)
    ax.set_aspect("equal"); ax.axis("off")
    bar = max(v for v in (1, 2, 5, 10, 20, 50, 100, 200, 500) if v <= span * 0.3)
    x0, y0 = cx - span * 0.48, cy - span * 0.47
    ax.plot([x0, x0 + bar], [y0, y0], color=INK, lw=2.2, solid_capstyle="butt")
    ax.text(x0 + bar / 2, y0 + span * 0.015, f"{bar:g} m", ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.annotate("", xy=(cx + span * 0.46, cy + span * 0.44), xytext=(cx + span * 0.46, cy + span * 0.33),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1))
    ax.text(cx + span * 0.46, cy + span * 0.48, "N", ha="center", va="center", fontsize=8, weight="bold")
    # where the roof goes
    total = sum(a for _, a, _ in c["roof_use"]) or 1.0
    left = 0.0
    for _, a, col in c["roof_use"]:
        bx.barh(0, a / total, left=left, color=col, height=1.0, ec="white", lw=1.0)
        left += a / total
    bx.set_xlim(0, 1); bx.set_ylim(-0.5, 0.5); bx.axis("off")
    bx.set_title(f"Where the {_fmt(c['raw_area'])} m² roof goes", fontsize=7.5, loc="left", color=INK, pad=3)
    for i, (lab, a, col) in enumerate(c["roof_use"]):
        y = 0.11 - 0.042 * i
        fig.patches.append(plt.Rectangle((0.03, y - 0.012), 0.025, 0.026, transform=fig.transFigure,
                                         fc=col, ec=ACCENT if col == STRIP else "none", lw=0.6))
        fig.text(0.07, y, f"{lab}", fontsize=7, va="center", color=INK)
        fig.text(0.97, y, f"{_fmt(a)} m²  ({a / total:.0%})", fontsize=7, va="center", ha="right", color=INK)
    fig.savefig(path_or_buffer, format="png")
    plt.close(fig)


def generate_footprint_diagram(meter_coords: List[Tuple[float, float]], output_png_path: str) -> None:
    """Footprint-only roof plan (kept for backward compatibility)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)
    roof_plan_png({"meter_coords": meter_coords}, output_png_path)


def generate_svg_footprint(meter_coords: List[Tuple[float, float]]) -> str:
    """Inline SVG of the footprint (kept for backward compatibility)."""
    if not meter_coords or len(meter_coords) < 3:
        return '<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg"></svg>'
    xs, ys = [c[0] for c in meter_coords], [c[1] for c in meter_coords]
    w, h = max(max(xs) - min(xs), 1.0), max(max(ys) - min(ys), 1.0)
    m = max(w, h) * 0.1
    pts = " ".join(f"{x:.2f},{(max(ys) + min(ys) - y):.2f}" for x, y in meter_coords)
    return (f'<svg viewBox="{min(xs) - m:.2f} {min(ys) - m:.2f} {w + 2 * m:.2f} {h + 2 * m:.2f}" '
            f'xmlns="http://www.w3.org/2000/svg"><polygon points="{pts}" fill="{STRIP}" stroke="{ACCENT}" '
            f'stroke-width="{max(w, h) * 0.012:.2f}"/></svg>')


def _where(c: Dict[str, Any], link) -> List[str]:
    out = []
    if c["lat"] is not None:
        out.append(f"{c['lat']:.5f}, {c['lon']:.5f}")
    if c["way"]:
        out.append("OSM way " + link(f"https://www.openstreetmap.org/way/{c['way']}", str(c["way"])))
    if c["emirate"]:
        out.append(html.escape(f"{c['emirate']} ({c['utility']})" if c["utility"] else str(c["emirate"])))
    out.append(f"{html.escape(str(c['date']))} | SolarScan {html.escape(str(c['version']))}")
    return out


# ---------------------------------------------------------------- PDF
def generate_pdf_report(report_data: Dict[str, Any], output_pdf_path: str) -> None:
    """One-page A4 PDF report."""
    if not REPORTLAB_AVAILABLE:
        logging.warning("ReportLab is not installed; skipping PDF report generation.")
        return
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    c = build_report_content(report_data)
    esc = html.escape
    hx = colors.HexColor
    body = ParagraphStyle("b", fontName="Helvetica", fontSize=8.5, leading=10.8, textColor=hx(INK))
    small = ParagraphStyle("s", parent=body, fontSize=7.5, leading=9.2, textColor=hx(INK2))
    bold = ParagraphStyle("bd", parent=body, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=15, leading=18)
    h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=10.5, leading=13, spaceAfter=4)
    big = ParagraphStyle("big", parent=body, fontName="Helvetica-Bold", fontSize=15, leading=17, textColor=hx(ACCENT))

    def sub(s):  # Helvetica has no subscript-2 glyph
        return esc(s).replace("CO₂", "CO<sub>2</sub>")

    doc = SimpleDocTemplate(output_pdf_path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=10 * mm, title="Rooftop solar screening report",
                            author="SolarScan")
    W = A4[0] - 28 * mm
    link = lambda url, t: f'<a href="{url}" color="{ACCENT}">{esc(t)}</a>'  # noqa: E731
    story = [Paragraph("Rooftop solar screening report", h1), Paragraph(esc(c["address"]), bold),
             Paragraph(" | ".join(_where(c, link)), small), Spacer(1, 3.5 * mm)]

    tiles = Table([[Paragraph(f'<font size="7" color="{INK2}">{esc(k)}</font><br/>{esc(v)}<br/>'
                              f'<font size="7" color="{INK2}" face="Helvetica">{esc(s)}</font>', big)
                    for k, v, s in c["key"]]], colWidths=[W / 4] * 4)
    tiles.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, hx(LINE)), ("INNERGRID", (0, 0), (-1, -1), 0.5, hx(LINE)),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    story += [tiles, Spacer(1, 4 * mm)]

    def kv(rows, widths, third=False):
        if third:  # label | value (bold) | basis
            data = [[Paragraph(sub(a), small), Paragraph(sub(b), bold), Paragraph(sub(x), small)] for a, b, x in rows]
        else:      # label | value
            data = [[Paragraph(sub(a), small), Paragraph(sub(b), body)] for a, b in rows]
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, hx(LINE)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    lw, rw = W * 0.47, W * 0.53
    buf = io.BytesIO()
    roof_plan_png(report_data, buf)
    buf.seek(0)
    plan = Image(buf, width=lw - 4 * mm, height=(lw - 4 * mm) * ASPECT) if buf.getbuffer().nbytes else Spacer(1, 1)
    right = [Paragraph("System assumed", h2), kv(c["system"], [rw * 0.2, rw * 0.8]), Spacer(1, 3.5 * mm),
             Paragraph("Money", h2), kv(c["money"], [rw * 0.27, rw * 0.25, rw * 0.48], third=True)]
    mid = Table([[[Paragraph("Roof plan", h2), plan], right]], colWidths=[lw, rw])
    mid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm)]))
    story += [mid, Spacer(1, 3 * mm)]

    vals = [v for row in c["grid"] for v in row if math.isfinite(v)]
    lo, hi = (min(vals), max(vals)) if vals else (0, 1)
    gdata = [["Cost / price"] + [f"{r:.2f}" for r in c["tariffs"]]]
    gdata += [[_fmt(cst)] + [f"{v:.1f}" if math.isfinite(v) else "–" for v in row] for cst, row in zip(c["costs"], c["grid"])]
    gst = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9),
           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
           ("TEXTCOLOR", (0, 0), (-1, 0), hx(INK2)), ("TEXTCOLOR", (0, 0), (0, -1), hx(INK2)),
           ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    for i, row in enumerate(c["grid"], 1):
        for j, v in enumerate(row, 1):
            bg, fg = _heat(v, lo, hi)
            gst += [("BACKGROUND", (j, i), (j, i), hx(bg)), ("TEXTCOLOR", (j, i), (j, i), hx(fg))]
    bi, bj = c["base"][0] + 1, c["base"][1] + 1
    gst += [("BOX", (bj, bi), (bj, bi), 1.6, hx("#e07b2a")), ("FONTNAME", (bj, bi), (bj, bi), "Helvetica-Bold")]
    g = Table(gdata, colWidths=[lw * 0.24] + [lw * 0.17] * 4, hAlign="LEFT")
    g.setStyle(TableStyle(gst))
    lim = Table([[Paragraph(f"<b>{esc(a)}</b> {esc(b)}", body)] for a, b in c["limits"]], colWidths=[rw])
    lim.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), hx("#fdf3e7")), ("BOX", (0, 0), (-1, -1), 0.6, hx("#e9b77d")),
                             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    low = Table([[[Paragraph("Payback in years for other costs and prices", h2), g,
                   Paragraph("Rows: cost (AED/kWp). Columns: price (AED/kWh). Orange box: values used.", small)],
                  [Paragraph("Limits", h2), lim]]], colWidths=[lw, rw])
    low.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm)]))
    story += [low, Spacer(1, 4 * mm), Paragraph(esc(CREDITS), small)]
    doc.build(story)


# ---------------------------------------------------------------- HTML
def generate_html_report(report_data: Dict[str, Any], output_html_path: str) -> None:
    """Self-contained HTML report (roof figure embedded as PNG); prints on one A4 page."""
    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
    c = build_report_content(report_data)
    esc = html.escape
    buf = io.BytesIO()
    roof_plan_png(report_data, buf)
    plan = (f'<img alt="Roof plan with edge strip, usable roof and module rows" '
            f'src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">' if buf.getbuffer().nbytes else "")
    where = " | ".join(_where(c, lambda url, t: f'<a href="{url}">{esc(t)}</a>'))
    tiles = "".join(f'<div class="tile"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div>'
                    f'<div class="s">{esc(s)}</div></div>' for k, v, s in c["key"])
    system = "".join(f"<tr><th>{esc(a)}</th><td>{esc(b)}</td></tr>" for a, b in c["system"])
    money = "".join(f"<tr><th>{esc(a)}</th><td><b>{esc(b)}</b></td><td class='n'>{esc(x)}</td></tr>"
                    for a, b, x in c["money"])
    vals = [v for row in c["grid"] for v in row if math.isfinite(v)]
    lo, hi = (min(vals), max(vals)) if vals else (0, 1)
    head = "".join(f"<th>{r:.2f}</th>" for r in c["tariffs"])
    body = ""
    for i, (cst, row) in enumerate(zip(c["costs"], c["grid"])):
        cells = ""
        for j, v in enumerate(row):
            bg, fg = _heat(v, lo, hi)
            base = " base" if (i, j) == c["base"] else ""
            cells += f'<td class="h{base}" style="background:{bg};color:{fg}">{v:.1f}</td>' if math.isfinite(v) \
                else "<td>–</td>"
        body += f"<tr><th>{_fmt(cst)}</th>{cells}</tr>"
    limits = "".join(f"<li><b>{esc(a)}</b> {esc(b)}</li>" for a, b in c["limits"])
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rooftop solar screening report: {esc(c['address'])}</title>
<style>
:root {{ --ink:{INK}; --ink2:{INK2}; --line:{LINE}; --accent:{ACCENT}; }}
* {{ box-sizing:border-box }}
body {{ margin:0; padding:24px 16px; background:#f5f6f8; color:var(--ink);
       font:13.5px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif }}
main {{ max-width:880px; margin:0 auto; background:#fff; border:1px solid var(--line); border-radius:10px; padding:26px }}
h1 {{ font-size:21px; margin:0 0 2px }} h2 {{ font-size:14px; margin:18px 0 6px }}
.addr {{ font-weight:600 }} .meta {{ color:var(--ink2); font-size:12px }} a {{ color:var(--accent) }}
.tiles {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:14px }}
.tile {{ border:1px solid var(--line); border-radius:8px; padding:8px 10px }}
.tile .k, .tile .s {{ font-size:11.5px; color:var(--ink2) }} .tile .v {{ font-size:21px; font-weight:700; color:var(--accent) }}
.two {{ display:grid; grid-template-columns:0.82fr 1fr; gap:22px; align-items:start }}
.two img {{ width:100%; height:auto }}
table {{ border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums }}
td, th {{ padding:4px 6px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:12.5px }}
th {{ font-weight:400; color:var(--ink2); white-space:nowrap }} td.n {{ color:var(--ink2); font-size:11.5px }}
.grid td, .grid th {{ text-align:center; border:2px solid #fff }} .grid td.base {{ outline:2px solid #e07b2a; outline-offset:-2px; font-weight:700 }}
.note {{ font-size:11.5px; color:var(--ink2); margin:4px 0 0 }}
.limits {{ background:#fdf3e7; border:1px solid #e9b77d; border-radius:8px; padding:8px 12px; margin:0; list-style:none }}
.limits li {{ margin:3px 0 }}
footer {{ margin-top:16px; font-size:11px; color:var(--ink2) }}
@media (max-width:640px) {{ .two, .tiles {{ grid-template-columns:1fr 1fr }} .two {{ grid-template-columns:1fr }} main {{ padding:16px }} }}
@media print {{ body {{ background:#fff; padding:0 }} main {{ border:0; padding:0; max-width:none }} @page {{ size:A4; margin:12mm }} }}
</style></head>
<body><main>
<h1>Rooftop solar screening report</h1>
<div class="addr">{esc(c['address'])}</div>
<div class="meta">{where}</div>
<div class="tiles">{tiles}</div>
<div class="two">
  <section><h2>Roof plan</h2>{plan}</section>
  <section><h2>System assumed</h2><table>{system}</table>
    <h2>Money</h2><table>{money}</table></section>
</div>
<div class="two">
  <section><h2>Payback in years for other costs and prices</h2>
    <table class="grid"><tr><th>Cost / price</th>{head}</tr>{body}</table>
    <p class="note">Rows: cost (AED/kWp). Columns: price (AED/kWh). Orange box: values used.</p></section>
  <section><h2>Limits</h2><ul class="limits">{limits}</ul></section>
</div>
<footer>{esc(CREDITS)}</footer>
</main></body></html>"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(page)
