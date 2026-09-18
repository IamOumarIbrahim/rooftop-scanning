"""
Generates publication-quality figures for the IEEE conference paper.
Outputs PDF and PNG formats to manuscript/figures/.
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.ticker as ticker
from PIL import Image
from shapely.geometry import Polygon as ShapelyPolygon

from solarscan.fixtures import load_fixture
from solarscan.geometry import latlon_to_meters, calculate_shoelace_area, calculate_usable_area
from solarscan.yield_estimate import calculate_orientation_derate, estimate_annual_yield

# Professional typography and sizing for IEEE double-column format
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 10,
    'lines.linewidth': 1.5,
    'grid.linewidth': 0.5,
    'grid.alpha': 0.5,
    'axes.grid': True,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

OUT_DIR = os.path.join("manuscript", "figures")
os.makedirs(OUT_DIR, exist_ok=True)


def generate_figure_pipeline_architecture():
    """Generates schematic block diagram of the automated pre-feasibility pipeline."""
    fig, ax = plt.subplots(figsize=(7.16, 2.1), dpi=300)
    ax.axis('off')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 36)

    stages = [
        {
            "num": "STAGE 1",
            "title": "Query Ingestion",
            "x": 1.0, "w": 16.6,
            "items": ["Address / Geocode", "GPS Coordinates", "Google Maps URL"],
            "badge": "Centroid Lat/Lon"
        },
        {
            "num": "STAGE 2",
            "title": "OSM Retrieval",
            "x": 21.0, "w": 16.6,
            "items": ["Overpass API QL", "Search Radius 250 m", "Building Way Filter"],
            "badge": "Vector GeoJSON"
        },
        {
            "num": "STAGE 3",
            "title": "Geometric Sizing",
            "x": 41.0, "w": 16.6,
            "items": ["Equirectangular Proj.", "Shoelace Area (A)", "Setback Buffer (s)"],
            "badge": "Net Usable Area"
        },
        {
            "num": "STAGE 4",
            "title": "PV Yield Model",
            "x": 61.0, "w": 16.6,
            "items": ["Dominant Azimuth", "Orientation Derate", "Regional Solar PSH"],
            "badge": "Annual MWh Yield"
        },
        {
            "num": "STAGE 5",
            "title": "Feasibility",
            "x": 81.0, "w": 16.6,
            "items": ["Turnkey CAPEX Model", "Utility Tariff Savings", "Simple Payback (Yrs)"],
            "badge": "Payback & ROI"
        }
    ]

    for st in stages:
        x, w = st["x"], st["w"]
        # Main card
        card = FancyBboxPatch(
            (x, 3.0), w, 30.0,
            boxstyle="Round,pad=0.2,rounding_size=0.8",
            facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=1.1, zorder=2
        )
        ax.add_patch(card)

        # Header box
        header = FancyBboxPatch(
            (x, 26.0), w, 7.0,
            boxstyle="Round,pad=0.2,rounding_size=0.8",
            facecolor='#1e3a8a', edgecolor='#1e3a8a', linewidth=1.0, zorder=3
        )
        ax.add_patch(header)
        
        ax.text(x + w / 2, 30.5, st["num"], ha='center', va='center',
                fontsize=6.8, fontweight='bold', color='#93c5fd', zorder=4)
        ax.text(x + w / 2, 27.8, st["title"], ha='center', va='center',
                fontsize=7.8, fontweight='bold', color='#ffffff', zorder=4)

        # Bullets
        y_text = 22.0
        for item in st["items"]:
            ax.plot(x + 1.2, y_text, marker='o', markersize=2.5, color='#0284c7', zorder=4)
            ax.text(x + 2.2, y_text, item, ha='left', va='center',
                    fontsize=6.6, color='#1e293b', zorder=4)
            y_text -= 4.0

        # Output badge pill at bottom
        badge_box = FancyBboxPatch(
            (x + 0.8, 4.2), w - 1.6, 3.8,
            boxstyle="Round,pad=0.1,rounding_size=0.5",
            facecolor='#e0f2fe', edgecolor='#7dd3fc', linewidth=0.7, zorder=4
        )
        ax.add_patch(badge_box)
        ax.text(x + w / 2, 6.1, st["badge"], ha='center', va='center',
                fontsize=6.8, fontweight='bold', color='#0369a1', zorder=5)

    # Connecting arrows
    for i in range(len(stages) - 1):
        x_start = stages[i]["x"] + stages[i]["w"] + 0.3
        x_end = stages[i + 1]["x"] - 0.3
        ax.annotate(
            '', xy=(x_end, 18.0), xytext=(x_start, 18.0),
            arrowprops=dict(facecolor='#0284c7', edgecolor='#0284c7', width=1.4, headwidth=4.5, headlength=5.0)
        )

    plt.subplots_adjust(left=0.005, right=0.995, top=0.98, bottom=0.02)
    fig.savefig(os.path.join(OUT_DIR, "fig_pipeline_architecture.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "fig_pipeline_architecture.png"))
    plt.close(fig)
    print("Generated fig_pipeline_architecture")


def generate_figure_validation_scatter():
    """Generates parity scatter plot comparing OSM footprint area vs Ground Truth Reference."""
    csv_path = os.path.join("data", "validation_buildings.csv")
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    ref_areas = np.array([float(r["reference_area_m2"]) for r in rows])
    osm_areas = np.array([float(r["osm_area_m2"]) for r in rows])
    categories = [r["category"] for r in rows]

    cat_markers = {
        "Academic": ("o", "#2563eb", "Academic"),
        "Commercial": ("s", "#dc2626", "Commercial"),
        "Industrial": ("^", "#d97706", "Industrial")
    }

    fig, ax = plt.subplots(figsize=(3.4, 3.2), dpi=300)
    
    line_x = np.logspace(np.log10(90), np.log10(250000), 100)
    ax.plot(line_x, line_x, 'k--', linewidth=1.0, label='Ideal 1:1 Parity')
    ax.plot(line_x, line_x * 0.90, ':', color='#64748b', linewidth=0.8, label=r'$\pm 10\%$ Bounds')
    ax.plot(line_x, line_x * 1.10, ':', color='#64748b', linewidth=0.8)
    ax.fill_between(line_x, line_x * 0.90, line_x * 1.10, color='#f1f5f9', alpha=0.6)

    plotted_cats = set()
    for i in range(len(rows)):
        cat = categories[i]
        marker, color, label = cat_markers[cat]
        lbl = label if cat not in plotted_cats else ""
        ax.scatter(ref_areas[i], osm_areas[i], color=color, marker=marker, s=32, alpha=0.85, edgecolors='k', linewidth=0.4, label=lbl, zorder=5)
        plotted_cats.add(cat)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(80, 300000)
    ax.set_ylim(80, 300000)
    ax.set_xlabel(r"Reference Measurement Area $A_{\mathrm{ref}}$ (m$^2$)")
    ax.set_ylabel(r"OSM Footprint Area $A_{\mathrm{osm}}$ (m$^2$)")
    ax.legend(loc='lower right', frameon=True, framealpha=0.92, fontsize=7)

    fig.savefig(os.path.join(OUT_DIR, "fig_validation_scatter.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "fig_validation_scatter.png"))
    plt.close(fig)
    print("Generated fig_validation_scatter")


def generate_figure_error_distribution():
    """Generates categorical relative percentage error distribution."""
    csv_path = os.path.join("data", "validation_buildings.csv")
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    cats = ["Academic", "Commercial", "Industrial"]
    cat_errors = {c: [] for c in cats}
    for r in rows:
        if r["category"] in cat_errors:
            cat_errors[r["category"]].append(float(r["rel_error_pct"]))

    fig, ax = plt.subplots(figsize=(3.4, 2.7), dpi=300)
    data_to_plot = [cat_errors[c] for c in cats]

    bp = ax.boxplot(
        data_to_plot,
        tick_labels=cats,
        patch_artist=True,
        widths=0.42,
        medianprops=dict(color='#0f172a', linewidth=1.5),
        boxprops=dict(facecolor='#93c5fd', color='#1e3a8a', linewidth=1.0),
        whiskerprops=dict(color='#1e3a8a', linewidth=1.0),
        capprops=dict(color='#1e3a8a', linewidth=1.0)
    )

    np.random.seed(42)
    for idx, c in enumerate(cats, 1):
        y = cat_errors[c]
        x = np.random.normal(idx + 0.18, 0.03, size=len(y))
        ax.scatter(x, y, color='#1e3a8a', alpha=0.75, s=20, edgecolors='none', zorder=4)

    ax.axhline(0, color='black', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.axhline(-4.54, color='#dc2626', linestyle=':', linewidth=1.0, label=r'Mean Bias ($-4.54\%$)')
    ax.set_ylabel(r"Relative Footprint Error (%)")
    ax.legend(loc='upper right', frameon=True, framealpha=0.92, fontsize=7)
    ax.set_ylim(-8.0, 0.5)

    fig.savefig(os.path.join(OUT_DIR, "fig_error_distribution.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "fig_error_distribution.png"))
    plt.close(fig)
    print("Generated fig_error_distribution")


def generate_figure_satellite_vs_osm_comparison():
    """
    Generates side-by-side visual comparison within a single column:
    (a) High-resolution satellite tracing (Google Earth)
    (b) Crowdsourced OpenStreetMap building polygon (Inchcape Shipping / JAFZA)
    """
    im1_path = os.path.join(OUT_DIR, "user_trace_google_earth.png")
    im2_path = os.path.join(OUT_DIR, "user_trace_osm.png")

    if not (os.path.exists(im1_path) and os.path.exists(im2_path)):
        print("Skipping satellite vs osm comparison figure (images not found)")
        return

    im1 = Image.open(im1_path)
    im2 = Image.open(im2_path)

    # Crop both images to identical aspect ratio (1.25) so they align perfectly
    im1_cropped = im1.crop((0, 0, 735, 588))
    im2_cropped = im2.crop((0, 10, 534, 437))

    fig, axes = plt.subplots(1, 2, figsize=(3.4, 2.0), dpi=300)
    
    axes[0].imshow(im1_cropped)
    axes[0].set_title("(a) Satellite Parapet Trace\n(Google Earth)", fontsize=7, fontweight='bold')
    axes[0].axis('off')

    axes[1].imshow(im2_cropped)
    axes[1].set_title("(b) Vector Footprint\n(OpenStreetMap)", fontsize=7, fontweight='bold')
    axes[1].axis('off')

    plt.tight_layout(pad=0.3)
    fig.savefig(os.path.join(OUT_DIR, "fig_satellite_vs_osm_comparison.pdf"), bbox_inches='tight', dpi=300)
    fig.savefig(os.path.join(OUT_DIR, "fig_satellite_vs_osm_comparison.png"), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print("Generated fig_satellite_vs_osm_comparison")


def generate_figure_sensitivity_setback():
    """Plots usable rooftop area fraction vs setback distance for three typologies."""
    setbacks = np.linspace(0.0, 3.0, 25)
    
    cases = [
        (r"Small Commercial (1,222 m$^2$)", 1221.88, 142.0, '#7c3aed', '--'),
        (r"Institutional W5 (1,610 m$^2$)", 1610.02, 165.4, '#2563eb', '-'),
        (r"Commercial Mall (36,000 m$^2$)", 36155.41, 837.33, '#dc2626', '-.')
    ]

    fig, ax = plt.subplots(figsize=(3.4, 2.85), dpi=300)

    for label, area, p, color, ls in cases:
        usable_fractions = [calculate_usable_area(area, p, s, 0.0) / area * 100.0 for s in setbacks]
        ax.plot(setbacks, usable_fractions, label=label, color=color, linestyle=ls, linewidth=1.6)

    ax.axvline(1.5, color='#64748b', linestyle=':', linewidth=1.0)
    ax.text(1.55, 35, "Standard 1.5 m\nSetback", color='#475569', fontsize=7.2,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.85))

    ax.set_xlim(0.0, 3.0)
    ax.set_ylim(0.0, 105.0)
    ax.set_xlabel(r"Perimeter Setback Distance $s$ (m)")
    ax.set_ylabel(r"Usable Roof Fraction $A_{\mathrm{usable}} / A_{\mathrm{raw}}$ (%)")
    ax.legend(loc='lower left', frameon=True, framealpha=0.92, fontsize=7)

    plt.tight_layout(pad=0.3)
    fig.savefig(os.path.join(OUT_DIR, "fig_sensitivity_setback.pdf"), bbox_inches='tight', dpi=300)
    fig.savefig(os.path.join(OUT_DIR, "fig_sensitivity_setback.png"), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print("Generated fig_sensitivity_setback")


def generate_figure_sensitivity_azimuth_tilt():
    """Generates 2D contour/surface plot of specific annual yield (kWh/kWp) vs azimuth and tilt."""
    azimuths = np.linspace(0, 360, 73)
    tilts = np.linspace(0, 45, 46)
    AZ, TI = np.meshgrid(azimuths, tilts)
    
    YIELD = np.zeros_like(AZ)
    for i in range(len(tilts)):
        for j in range(len(azimuths)):
            kwh = estimate_annual_yield(
                1.0, tilt_deg=tilts[i], azimuth_deg=azimuths[j],
                peak_sun_hours_per_day=5.5, system_loss_factor=0.85
            )
            YIELD[i, j] = kwh

    fig, ax = plt.subplots(figsize=(3.4, 2.7), dpi=300)
    cs = ax.contourf(AZ, TI, YIELD, levels=14, cmap='viridis')
    lines = ax.contour(AZ, TI, YIELD, levels=7, colors='white', linewidths=0.4, alpha=0.6)
    ax.clabel(lines, inline=True, fontsize=6, fmt='%1.0f')

    cbar = fig.colorbar(cs, ax=ax, orientation='vertical', pad=0.03)
    cbar.set_label("Annual Yield (kWh / kWp / yr)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    ax.scatter([180], [20], color='#ef4444', marker='*', s=80, edgecolor='white', linewidth=0.5, label=r'Optimal ($180^\circ$, $20^\circ$)')
    ax.set_xlabel(r"Roof Azimuth Angle $\psi$ (deg)")
    ax.set_ylabel(r"Panel Tilt Angle $\beta$ (deg)")
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.set_xticklabels([r'N ($0^\circ$)', r'E ($90^\circ$)', r'S ($180^\circ$)', r'W ($270^\circ$)', r'N ($360^\circ$)'])
    ax.legend(loc='upper right', frameon=True, framealpha=0.92, fontsize=7)

    fig.savefig(os.path.join(OUT_DIR, "fig_sensitivity_azimuth_tilt.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "fig_sensitivity_azimuth_tilt.png"))
    plt.close(fig)
    print("Generated fig_sensitivity_azimuth_tilt")


def generate_figure_w5_case_study():
    """Generates detailed footprint geometry and setback overlay for University of Sharjah W5."""
    fixture_path = os.path.join("data", "fixtures", "uos_w5.json")
    data = load_fixture(fixture_path)
    coords = data["polygon_coords"]
    meters = latlon_to_meters(coords)

    xs = [pt[0] for pt in meters] + [meters[0][0]]
    ys = [pt[1] for pt in meters] + [meters[0][1]]

    # Shapely polygon for exact setback calculation
    poly = ShapelyPolygon(meters)
    setback_poly = poly.buffer(-1.5)

    fig, ax = plt.subplots(figsize=(3.4, 3.4), dpi=300)

    # 1. Gross Footprint
    ax.fill(xs, ys, color='#bfdbfe', alpha=0.5, label=r'Gross Footprint (1,610.0 m$^2$)')
    ax.plot(xs, ys, color='#1e3a8a', linewidth=1.6, label=r'Gross Boundary ($P = 165.4$ m)')
    ax.scatter([pt[0] for pt in meters], [pt[1] for pt in meters], color='#1e3a8a', s=14, zorder=5)

    # 2. Net Usable Area with 1.5m setback
    if not setback_poly.is_empty:
        if setback_poly.geom_type == 'Polygon':
            s_xs, s_ys = setback_poly.exterior.xy
            ax.fill(s_xs, s_ys, color='#fef08a', alpha=0.5, label=r'Usable PV Area (1,361.9 m$^2$)')
            ax.plot(s_xs, s_ys, color='#ca8a04', linestyle='--', linewidth=1.2, label='1.5 m Setback Boundary')
        elif setback_poly.geom_type == 'MultiPolygon':
            for p_idx, p in enumerate(setback_poly.geoms):
                s_xs, s_ys = p.exterior.xy
                lbl = r'Usable PV Area (1,361.9 m$^2$)' if p_idx == 0 else ""
                lbl_line = '1.5 m Setback Boundary' if p_idx == 0 else ""
                ax.fill(s_xs, s_ys, color='#fef08a', alpha=0.5, label=lbl)
                ax.plot(s_xs, s_ys, color='#ca8a04', linestyle='--', linewidth=1.2, label=lbl_line)

    # 3. Dominant orientation axis vector (68.2 deg clockwise from North)
    cent_x = sum(pt[0] for pt in meters) / len(meters)
    cent_y = sum(pt[1] for pt in meters) / len(meters)
    rad = np.radians(90 - 68.2)
    vec_len = 22.0
    dx = vec_len * np.cos(rad)
    dy = vec_len * np.sin(rad)
    arrow = FancyArrowPatch(
        (cent_x, cent_y), (cent_x + dx, cent_y + dy),
        arrowstyle='->,head_width=4,head_length=6',
        color='#dc2626', linewidth=1.8, label=r'Dominant Axis ($68.2^\circ$)'
    )
    ax.add_patch(arrow)

    # 4. Crisp Compass North arrow in top-right
    ax.annotate(
        'N', xy=(0.90, 0.94), xycoords='axes fraction', ha='center', va='bottom',
        fontsize=8.5, fontweight='bold', color='#0f172a'
    )
    ax.annotate(
        '', xy=(0.90, 0.93), xytext=(0.90, 0.82), xycoords='axes fraction',
        arrowprops=dict(facecolor='#0f172a', edgecolor='#0f172a', width=0.8, headwidth=3.5, headlength=4.5)
    )

    ax.set_aspect('equal', 'box')
    ax.set_xlim(-28, 45)
    ax.set_ylim(-26, 48)
    ax.set_xlabel("Local X (East, meters)", fontsize=8)
    ax.set_ylabel("Local Y (North, meters)", fontsize=8)
    ax.tick_params(labelsize=7.5)

    # Legend in upper-left whitespace
    ax.legend(loc='upper left', frameon=True, framealpha=0.92, fontsize=6.2, edgecolor='#cbd5e1')

    fig.savefig(os.path.join(OUT_DIR, "fig_w5_case_study.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "fig_w5_case_study.png"))
    plt.close(fig)
    print("Generated fig_w5_case_study")


def main():
    print("Generating all paper figures...")
    generate_figure_pipeline_architecture()
    generate_figure_validation_scatter()
    generate_figure_error_distribution()
    generate_figure_satellite_vs_osm_comparison()
    generate_figure_sensitivity_setback()
    generate_figure_sensitivity_azimuth_tilt()
    generate_figure_w5_case_study()
    print("All figures successfully generated in manuscript/figures/!")


if __name__ == "__main__":
    main()


