"""
Reporting module for rooftop solar pre-feasibility analysis.
Generates publication-quality diagrams, single-page summary PDF reports,
and self-contained HTML reports.
"""

import os
from typing import Dict, Any, List, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_footprint_diagram(meter_coords: List[Tuple[float, float]], output_png_path: str) -> None:
    """
    Generates a 2D Cartesian diagram of the building footprint polygon.
    """
    if not meter_coords or len(meter_coords) < 3:
        return
    
    os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)
    
    x = [c[0] for c in meter_coords] + [meter_coords[0][0]]
    y = [c[1] for c in meter_coords] + [meter_coords[0][1]]
    
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.plot(x, y, color='#1e3a8a', linewidth=2, label='Building Boundary')
    ax.fill(x, y, color='#3b82f6', alpha=0.35, label='Rooftop Area')
    ax.set_title("Extracted Building Footprint", fontsize=11, fontweight='bold', pad=10)
    ax.set_xlabel("East-West Distance (m)", fontsize=10)
    ax.set_ylabel("North-South Distance (m)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_aspect('equal', 'box')
    
    plt.tight_layout()
    plt.savefig(output_png_path, format='png')
    plt.close(fig)


def generate_pdf_report(report_data: Dict[str, Any], output_pdf_path: str) -> None:
    """
    Generates a formal PDF pre-feasibility report using ReportLab.
    """
    if not REPORTLAB_AVAILABLE:
        return
        
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    diagram_png = output_pdf_path.replace('.pdf', '_temp_diag.png')
    generate_footprint_diagram(report_data.get("meter_coords", []), diagram_png)
    
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=12
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=10,
        spaceAfter=6
    )

    story = []
    story.append(Paragraph("SolarScan Feasibility Assessment", title_style))
    story.append(Spacer(1, 8))
    
    address = report_data.get("address", "N/A")
    story.append(Paragraph(f"<b>Location:</b> {address}", styles['Normal']))
    story.append(Spacer(1, 8))
    
    if os.path.exists(diagram_png):
        story.append(Image(diagram_png, width=380, height=220))
        story.append(Spacer(1, 10))
        
    story.append(Paragraph("System Sizing & Yield Summary", h2_style))
    
    table_data = [
        ["Parameter", "Estimated Value"],
        ["Gross Footprint Area", f"{report_data.get('raw_area', 0.0):,.2f} m²"],
        ["Net Usable Area (after setback)", f"{report_data.get('usable_area', 0.0):,.2f} m²"],
        ["Perimeter Setback Distance", f"{report_data.get('setback_m', 1.5):.2f} m"],
        ["Module Efficiency", f"{report_data.get('module_efficiency', 0.20)*100:.1f}%"],
        ["Rated DC Capacity", f"{report_data.get('dc_capacity_kw', 0.0):,.2f} kW DC"],
        ["Recommended Inverter Band", f"{report_data.get('ac_capacity_kw', 0.0):,.2f} kW AC"],
        ["Dominant Roof Azimuth", f"{report_data.get('azimuth_deg', 180.0):.1f}°"],
        ["Array Tilt Angle", f"{report_data.get('tilt_deg', 15.0):.1f}°"],
        ["Estimated Annual Energy Yield", f"{report_data.get('annual_kwh', 0.0):,.2f} kWh/yr"],
        ["Assumed Electricity Tariff", f"{report_data.get('rate_aed', 0.38):.2f} AED/kWh"],
        ["Simple Payback Period", f"{report_data.get('payback_years', 0.0):.2f} years"],
    ]
    
    t = Table(table_data, colWidths=[240, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    
    story.append(t)
    doc.build(story)
    
    if os.path.exists(diagram_png):
        try:
            os.remove(diagram_png)
        except Exception:
            pass


def generate_svg_footprint(meter_coords: List[Tuple[float, float]]) -> str:
    """
    Generates an inline SVG polygon markup string for web reports.
    """
    if not meter_coords or len(meter_coords) < 3:
        return '<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg"></svg>'

    xs = [c[0] for c in meter_coords]
    ys = [c[1] for c in meter_coords]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    w = max_x - min_x
    h = max_y - min_y
    w = max(w, 1.0)
    h = max(h, 1.0)

    margin = max(w, h) * 0.1
    vb_min_x = min_x - margin
    vb_min_y = min_y - margin
    vb_w = w + 2 * margin
    vb_h = h + 2 * margin

    points_str = " ".join(f"{x:.2f},{(max_y + min_y - y):.2f}" for x, y in meter_coords)
    stroke_width = max(w, h) * 0.012

    return (
        f'<svg viewBox="{vb_min_x:.2f} {vb_min_y:.2f} {vb_w:.2f} {vb_h:.2f}" '
        f'xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; max-height: 350px;">\n'
        f'  <polygon points="{points_str}" fill="#3b82f6" fill-opacity="0.35" '
        f'stroke="#1e3a8a" stroke-width="{stroke_width:.2f}" stroke-linejoin="round" />\n'
        f'</svg>'
    )


def generate_html_report(report_data: Dict[str, Any], output_html_path: str) -> None:
    """
    Generates an offline, self-contained HTML report with embedded SVG.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
    svg_code = generate_svg_footprint(report_data.get("meter_coords", []))
    address = report_data.get("address", "N/A")
    raw_area = report_data.get("raw_area", 0.0)
    usable_area = report_data.get("usable_area", 0.0)
    setback_m = report_data.get("setback_m", 1.5)
    module_eff = report_data.get("module_efficiency", 0.20)
    dc_capacity_kw = report_data.get("dc_capacity_kw", 0.0)
    ac_capacity_kw = report_data.get("ac_capacity_kw", 0.0)
    azimuth_deg = report_data.get("azimuth_deg", 180.0)
    tilt_deg = report_data.get("tilt_deg", 15.0)
    annual_kwh = report_data.get("annual_kwh", 0.0)
    rate_aed = report_data.get("rate_aed", 0.38)
    payback_years = report_data.get("payback_years", 0.0)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar Feasibility Report - {address}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 2rem 1rem; display: flex; justify-content: center; }}
        .container {{ max-width: 800px; width: 100%; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); padding: 2rem; border: 1px solid #e2e8f0; }}
        h1 {{ font-size: 1.4rem; text-align: center; margin-bottom: 1.2rem; }}
        .meta {{ background: #f1f5f9; padding: 0.75rem 1rem; border-radius: 6px; font-weight: 500; margin-bottom: 1.5rem; }}
        .diagram {{ background: #fafafa; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; }}
        th, td {{ padding: 0.7rem 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 0.95rem; }}
        th {{ background: #0f172a; color: #ffffff; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Rooftop Solar Feasibility Assessment</h1>
        <div class="meta">Location: {address}</div>
        <div class="diagram">{svg_code}</div>
        <table>
            <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
            <tbody>
                <tr><td>Gross Footprint Area</td><td>{raw_area:,.2f} m²</td></tr>
                <tr><td>Net Usable Area</td><td>{usable_area:,.2f} m²</td></tr>
                <tr><td>Setback Distance</td><td>{setback_m:.2f} m</td></tr>
                <tr><td>Module Efficiency</td><td>{module_eff*100:.1f}%</td></tr>
                <tr><td>DC Array Capacity</td><td>{dc_capacity_kw:,.2f} kW DC</td></tr>
                <tr><td>Inverter Capacity</td><td>{ac_capacity_kw:,.2f} kW AC</td></tr>
                <tr><td>Roof Azimuth</td><td>{azimuth_deg:.1f}°</td></tr>
                <tr><td>Panel Tilt</td><td>{tilt_deg:.1f}°</td></tr>
                <tr><td>Annual Energy Yield</td><td>{annual_kwh:,.2f} kWh/yr</td></tr>
                <tr><td>Electricity Tariff</td><td>{rate_aed:.2f} AED/kWh</td></tr>
                <tr><td>Simple Payback Period</td><td>{payback_years:.2f} years</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html)
