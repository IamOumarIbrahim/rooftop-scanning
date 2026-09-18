"""
Generates LaTeX tables for the IEEE conference manuscript.
Outputs .tex files to manuscript/tables/.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import csv
import numpy as np

TABLES_DIR = os.path.join("manuscript", "tables")
os.makedirs(TABLES_DIR, exist_ok=True)


def generate_table_prior_art():
    """Generates comparative prior-art matrix table."""
    tex = r"""\begin{table*}[t]
\centering
\caption{Systematic Comparison of Rooftop Photovoltaic Potential and Screening Methodologies}
\label{tab:prior_art}
\footnotesize
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{p{2.9cm}p{2.6cm}ccp{2.5cm}p{5.6cm}}
\toprule
\textbf{Study / Platform} & \textbf{Primary Data Source} & \textbf{Open Source} & \textbf{End-to-End} & \textbf{Demonstrated Region} & \textbf{Key Limitation for First Decision} \\
\midrule
Google Project Sunroof & Airborne LiDAR & No & Yes & USA, Germany & Zero coverage in UAE, GCC, and Global South; proprietary. \\
Google Solar API & High-Res Satellite & No & Partial & $\sim$40 OECD nations & Paid per-request API; zero coverage in UAE and GCC. \\
Assouline et al. (2017) \cite{assouline2017} & Cadastre + LiDAR & No & No & Switzerland & Regional potential only; requires municipal GIS cadastre. \\
Mainzer et al. (2017) \cite{mainzer2017} & OpenStreetMap + Aerial & No & No & Germany & European pitched roofs; no automated address screener. \\
Walch et al. (2020) \cite{walch2020} & 3D CityGML (LoD2) & Partial & No & Switzerland & Requires 3D municipal models unavailable in MENA. \\
Rees et al. (2025) \cite{rees2025} & Airborne LiDAR + OSM & Open Data & No & Troms\o, Norway & High-latitude focus; requires desktop GIS software. \\
pvlib-python \cite{holmgren2018} & None (Physics Engine) & Yes & Partial & Global & Requires pre-determined roof geometry; no spatial extraction. \\
\textbf{This Work (SolarScan)} & \textbf{OpenStreetMap Only} & \textbf{Yes} & \textbf{Yes} & \textbf{United Arab Emirates} & \textbf{Targeted for flat roofs; zero API fees or GIS dependencies.} \\
\bottomrule
\end{tabular}
\end{table*}
"""
    with open(os.path.join(TABLES_DIR, "tab_prior_art.tex"), "w", encoding="utf-8") as f:
        f.write(tex)
    print("Generated tab_prior_art.tex")


def generate_table_validation_dataset():
    """Generates the full 24-building empirical validation table."""
    csv_path = os.path.join("data", "validation_buildings.csv")
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    lines = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Empirical Validation Dataset: OSM Footprint vs. Independent High-Resolution Satellite Reference Measurements ($N=24$)}")
    lines.append(r"\label{tab:validation_dataset}")
    lines.append(r"\footnotesize")
    lines.append(r"\setlength{\tabcolsep}{4.0pt}")
    lines.append(r"\resizebox{\textwidth}{!}{%")
    lines.append(r"\begin{tabular}{lllcrrrr}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{ID} & \textbf{Building Facility Name} & \textbf{Emirate} & \textbf{Category} & \textbf{$A_{\mathrm{osm}}$ (m$^2$)} & \textbf{$A_{\mathrm{ref}}$ (m$^2$)} & \textbf{$|\Delta A|$ (m$^2$)} & \textbf{Error (\%)} \\")
    lines.append(r"\midrule")

    for r in rows:
        bid = r["id"].replace("_", r"\_")
        name = r["name"].replace("&", r"\&")
        em = r["emirate"]
        cat = r["category"]
        osm_a = float(r["osm_area_m2"])
        ref_a = float(r["reference_area_m2"])
        abs_err = float(r["abs_error_m2"])
        rel_err = float(r["rel_error_pct"])
        lines.append(f"{bid} & {name} & {em} & {cat} & {osm_a:,.2f} & {ref_a:,.2f} & {abs_err:,.2f} & {rel_err:+.2f}\\% \\\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}%")
    lines.append(r"}")
    lines.append(r"\end{table*}")

    with open(os.path.join(TABLES_DIR, "tab_validation_dataset.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Generated tab_validation_dataset.tex")


def generate_table_error_metrics():
    """Generates the categorical error summary table."""
    from experiments.run_validation import compute_metrics
    res = compute_metrics()

    lines = []
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Statistical Validation Metrics Categorized by Building Typology}")
    lines.append(r"\label{tab:error_metrics}")
    lines.append(r"\footnotesize")
    lines.append(r"\setlength{\tabcolsep}{3.0pt}")
    lines.append(r"\begin{tabular}{lcccc}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Typology} & \textbf{Count} & \textbf{MAPE (\%)} & \textbf{MBE (\%)} & \textbf{Error Range (\%)} \\")
    lines.append(r"\midrule")

    for cat, stats in res["categorical"].items():
        lines.append(f"{cat} & {stats['count']} & {stats['mape']:.2f}\\% & {stats['mbe']:.2f}\\% & [{stats['min_err']:+.2f}\\%, {stats['max_err']:+.2f}\\%] \\\\")

    lines.append(r"\midrule")
    min_e = min(float(r['rel_error_pct']) for r in res['rows'])
    max_e = max(float(r['rel_error_pct']) for r in res['rows'])
    lines.append(f"\\textbf{{Overall}} & \\textbf{{{res['n_buildings']}}} & \\textbf{{{res['mape']:.2f}\\%}} & \\textbf{{{res['mbe']:.2f}\\%}} & \\textbf{{[{min_e:+.2f}\\%, {max_e:+.2f}\\%]}} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    with open(os.path.join(TABLES_DIR, "tab_error_metrics.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Generated tab_error_metrics.tex")


def generate_table_w5_case_study():
    """Generates case study numerical parameters table for UoS W5 computed from functions."""
    from solarscan.geometry import calculate_usable_area
    from solarscan.sizing import calculate_dc_capacity, recommend_inverter_capacity, calculate_module_count
    from solarscan.yield_estimate import calculate_orientation_derate, estimate_annual_yield, estimate_simple_payback

    raw_area = 1610.02
    ref_area = 1699.86
    p = 165.40
    s = 1.50
    usable_area = calculate_usable_area(raw_area, p, s)
    dc_cap = calculate_dc_capacity(usable_area, 0.20)
    inv_cap = recommend_inverter_capacity(dc_cap, 1.20)
    n_mods = calculate_module_count(dc_cap, 400.0)
    azimuth = 68.2
    tilt = 15.0
    derate = calculate_orientation_derate(azimuth, tilt)
    annual_kwh = estimate_annual_yield(dc_cap, tilt_deg=tilt, azimuth_deg=azimuth, peak_sun_hours_per_day=5.5, system_loss_factor=0.85)
    annual_mwh = annual_kwh / 1000.0
    tariff = 0.38
    annual_savings = annual_kwh * tariff
    capex = dc_cap * 1000.0
    payback = estimate_simple_payback(annual_kwh, tariff, cost_per_kw=1000.0, dc_capacity_kw=dc_cap)
    spec_yield = annual_kwh / dc_cap
    co2_tonnes = (annual_kwh * 0.42) / 1000.0

    tex = f"""\\begin{{table}}[t]
\\centering
\\caption{{Pre-Feasibility Technical and Financial Results for UoS W5}}
\\label{{tab:w5_case_study}}
\\footnotesize
\\resizebox{{\\columnwidth}}{{!}}{{%
\\begin{{tabular}}{{llr}}
\\toprule
\\textbf{{Parameter}} & \\textbf{{Unit}} & \\textbf{{Value}} \\\\
\\midrule
Building Identifier & -- & UoS W5 (CS Dept) \\\\
Coordinates & deg & $25.28933^\\circ$ N, $55.47831^\\circ$ E \\\\
OSM Way Identifier & -- & 204709053 \\\\
Gross Footprint Area ($A_{{\\mathrm{{raw}}}}$) & m$^2$ & {raw_area:,.2f} \\\\
Reference Area ($A_{{\\mathrm{{ref}}}}$) & m$^2$ & {ref_area:,.2f} \\\\
Agreement Ratio & \\% & {raw_area/ref_area*100:.2f}\\% \\\\
Footprint Perimeter ($P$) & m & {p:.2f} \\\\
Setback Buffer ($s$) & m & {s:.2f} \\\\
Setback Area ($P \\cdot s$) & m$^2$ & {p*s:.2f} \\\\
Net Usable Area ($A_{{\\mathrm{{usable}}}}$) & m$^2$ & {usable_area:,.2f} \\\\
Module Efficiency ($\\eta$) & \\% & 20.0\\% \\\\
Nameplate DC Capacity ($P_{{\\mathrm{{dc}}}}$) & kW DC & {dc_cap:.2f} \\\\
Target DC/AC Ratio (ILR) & -- & 1.20 \\\\
Inverter Capacity ($P_{{\\mathrm{{ac}}}}$) & kW AC & {inv_cap:.2f} \\\\
Estimated Modules (400 Wp) & units & {n_mods} \\\\
Dominant Azimuth ($\\psi$) & deg & {azimuth:.1f}$^\\circ$ \\\\
Array Tilt Angle ($\\beta$) & deg & {tilt:.1f}$^\\circ$ \\\\
Orientation Derate ($f_{{\\mathrm{{orient}}}}$) & -- & {derate:.4f} \\\\
Solar Resource (GHI / PSH) & kWh/m$^2$/day & 5.50 \\\\
Performance Ratio ($\\mathrm{{PR}}$) & -- & 0.85 \\\\
Annual Generation ($E_{{\\mathrm{{annual}}}}$) & MWh/yr & {annual_mwh:.2f} \\\\
Specific Annual Yield & kWh/kWp/yr & {spec_yield:,.1f} \\\\
Avoided Carbon Emissions & tCO$_2$e/yr & {co2_tonnes:,.2f} \\\\
Electricity Tariff ($r$) & AED/kWh & {tariff:.2f} \\\\
Turnkey CAPEX (1,000~AED/kW) & AED & {capex:,.0f} \\\\
Annual Savings & AED/yr & {annual_savings:,.0f} \\\\
Simple Payback Period ($T_{{\\mathrm{{pb}}}}$) & years & {payback:.2f} \\\\
\\bottomrule
\\end{{tabular}}%
}}
\\end{{table}}
"""
    with open(os.path.join(TABLES_DIR, "tab_w5_case_study.tex"), "w", encoding="utf-8") as f:
        f.write(tex)
    print("Generated tab_w5_case_study.tex")


def generate_table_sensitivity_setback():
    """Generates numerical setback sensitivity table formatted cleanly for single-column IEEEtran."""
    tex = r"""\begin{table}[t]
\centering
\caption{Usable Rooftop Area Percentage vs Perimeter Setback Distance ($s$)}
\label{tab:sensitivity_setback}
\footnotesize
\setlength{\tabcolsep}{4.5pt}
\begin{tabular}{cccc}
\toprule
\textbf{Setback} & \textbf{Small Comm.} & \textbf{UoS W5} & \textbf{Mall} \\
\textbf{$s$ (m)} & \textbf{(1,222~m$^2$)} & \textbf{(1,610~m$^2$)} & \textbf{(36,155~m$^2$)} \\
\midrule
0.00 & 100.0\% & 100.0\% & 100.0\% \\
0.50 & 94.2\% & 94.9\% & 98.8\% \\
1.00 & 88.4\% & 89.7\% & 97.7\% \\
1.50 (Base) & 82.6\% & 84.6\% & 96.5\% \\
2.00 & 76.8\% & 79.5\% & 95.4\% \\
2.50 & 70.9\% & 74.3\% & 94.2\% \\
3.00 & 65.1\% & 69.2\% & 93.0\% \\
\midrule
$P/A$ Ratio & 0.116~m$^{-1}$ & 0.103~m$^{-1}$ & 0.023~m$^{-1}$ \\
\bottomrule
\end{tabular}
\end{table}
"""
    with open(os.path.join(TABLES_DIR, "tab_sensitivity_setback.tex"), "w", encoding="utf-8") as f:
        f.write(tex)
    print("Generated tab_sensitivity_setback.tex")


def main():
    print("Generating all LaTeX tables...")
    generate_table_prior_art()
    generate_table_validation_dataset()
    generate_table_error_metrics()
    generate_table_w5_case_study()
    generate_table_sensitivity_setback()
    print("All tables successfully generated in manuscript/tables/!")


if __name__ == "__main__":
    main()

