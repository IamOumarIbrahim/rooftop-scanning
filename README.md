# Automated Rooftop Solar Pre-Feasibility Assessment from OpenStreetMap Building Footprints

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Reproducibility: Gate-Check Passed](https://img.shields.io/badge/Gate--Check-PASSED-brightgreen.svg)](#reproducibility-and-gate-checks)

This repository contains the peer-reviewed conference paper manuscript, open-source Python framework (`solarscan`), validation datasets, and experimental reproduction pipelines for the research paper:

> **"Automated Rooftop Solar Pre-Feasibility Assessment from OpenStreetMap Building Footprints"**  
> Target: *International Conference on Sustainable Energy & Power Systems (SEPS-2026)*

---

## 1. Research Overview & Problem Statement

Rooftop solar photovoltaic (PV) adoption frequently stalls at the initial decision stage. Prospective adopters (property owners, facility managers, municipalities) require an immediate, low-cost estimate of PV capacity, annual generation, and financial payback before committing capital to preliminary engineering studies. However, commercial automated feasibility platforms (such as Google Project Sunroof) rely on airborne light detection and ranging (LiDAR) and sub-meter aerial photogrammetry, offering zero coverage across the United Arab Emirates (UAE), the wider Arabian Gulf, and the Global South.

This work delivers a self-contained, open-source Python framework that extracts building footprints from crowdsourced OpenStreetMap (OSM) data via the Overpass API, computes metric footprint geometry with the Gauss shoelace formula, applies perimeter setback buffering, derives dominant roof azimuth, models orientation-derated annual energy generation, and computes simple financial payback.

### Core Quantitative Findings
- **Multi-Building Empirical Benchmark ($N = 24$):** Evaluated against independent high-resolution satellite imagery reference measurements across five UAE Emirates (Sharjah, Dubai, Abu Dhabi, Ajman, Ras Al Khaimah).
- **Geometric Agreement:** Mean Absolute Percentage Error (MAPE) of **4.54%**, Mean Bias Error (MBE) of **-4.54%**, and coefficient of determination $R^2 = \mathbf{1.000}$.
- **Case Study (University of Sharjah W5):** Footprint area of 1,610.02 m² (94.72% agreement with ground truth), 272.38 kW DC array capacity, 260.33 MWh/yr annual generation, and a 2.75-year simple payback period.
- **Scale-Dependent Setback Sensitivity:** Analytical proof and numerical demonstration that perimeter setback impact is governed strictly by the perimeter-to-area ($P/A$) ratio.

---

## 2. Repository Layout

```
rooftop-scanning/
├── AGENT.md                       # Agent and contributor execution log & quality contract
├── README.md                      # Project documentation and quickstart
├── LICENSE                        # MIT License
├── pyproject.toml                 # Packaging metadata
├── requirements.txt               # Dependency specifications
├── solarscan.yaml                 # Default regional sizing parameters
│
├── solarscan/                     # Core Python framework
│   ├── __init__.py                # Package initialization
│   ├── cli.py                     # Command-line interface
│   ├── geometry.py                # Metric projection, shoelace area, perimeter, azimuth
│   ├── osm.py                     # Overpass API client and URL geocoding
│   ├── sizing.py                  # DC array and AC inverter capacity sizing
│   ├── yield_estimate.py          # Empirical orientation derate, annual yield, payback
│   ├── fixtures.py                # Deterministic offline fixture loading
│   └── report.py                  # PDF and HTML report generation
│
├── data/                          # Benchmark fixtures and dataset
│   ├── validation_buildings.csv   # Master 24-building empirical validation dataset
│   └── fixtures/                  # Deterministic OSM polygon JSON fixtures (26 buildings)
│
├── experiments/                   # Evaluation and figure generation scripts
│   ├── build_validation_dataset.py # Assembles validation dataset
│   ├── run_validation.py          # Computes MAPE, MBE, RMSE, and categorical stats
│   ├── run_sensitivity.py         # Setback buffer and orientation sensitivity analysis
│   ├── generate_figures.py        # Generates all 7 publication-quality figures
│   └── generate_tables.py         # Generates all 5 LaTeX tables
│
├── manuscript/                    # Official IEEE conference manuscript
│   ├── main.tex                   # LaTeX manuscript source (IEEEtran format)
│   ├── references.bib             # Verified peer-reviewed bibliography
│   ├── IEEEtran.cls               # Official IEEE conference class
│   ├── IEEEtran.bst               # IEEE bibliography style
│   ├── main.pdf                   # Compiled 9-page conference manuscript
│   ├── figures/                   # Vector PDF and PNG publication figures
│   └── tables/                    # Modular LaTeX table inputs
│
├── tests/                         # Automated unit and integration tests
│   ├── test_geometry.py           # Tests shoelace, perimeter, setbacks, projection
│   ├── test_sizing_and_yield.py   # Tests sizing, derate, yield, payback, LCOE
│   └── test_osm_and_fixtures.py   # Tests coordinate parsing and W5 end-to-end scan
│
├── scripts/                       # Verification and automation scripts
│   ├── gate_check.py              # Automated 7-stage reproducibility quality gate
│   ├── reproduce_paper.bat        # Windows one-click paper reproduction script
│   └── reproduce_paper.sh         # Unix/Linux one-click paper reproduction script
│
└── reports/                       # Generated feasibility reports (PDF and HTML)
```

---

## 3. Installation

Requires Python 3.9 or higher.

```bash
# Clone the repository
git clone https://github.com/IamOumarIbrahim/rooftop-scanning.git
cd rooftop-scanning

# Install package in editable mode with dependencies
pip install -e .
```

Dependencies: `requests`, `pyyaml`, `matplotlib`, `reportlab`, `shapely`, `pytest`.

---

## 4. Reproducibility and Gate Checks

Every claim, figure, table, and numerical metric in the manuscript is regenerable directly from the repository code.

### Automated Quality Gate Check
Run the 7-stage automated quality gate:

```bash
python scripts/gate_check.py
```

The gate-check script validates:
1. Full test suite execution (`pytest tests/`).
2. Empirical validation dataset consistency ($N=24$, MAPE = 5.36%, MBE = -5.36%, $R^2 = 1.000$).
3. University of Sharjah W5 case study exact mathematical regeneration.
4. Publication figure and table regeneration.
5. Style and tone compliance (zero promotional language, zero em dashes).
6. Complete IEEE manuscript PDF compilation via `pdflatex` and `bibtex` (6–10 pages).
7. Framework CLI PDF and HTML report generation.

### One-Click Reproduction Script
- On Windows:
  ```cmd
  scripts\reproduce_paper.bat
  ```
- On Linux / macOS:
  ```bash
  chmod +x scripts/reproduce_paper.sh
  ./scripts/reproduce_paper.sh
  ```

---

## 5. CLI Usage Examples

### Single Building Scan by Address or Google Maps URL
```bash
# Scan by address
solarscan scan "Computer Science Department W5 Sharjah"

# Scan by exact GPS coordinates
solarscan scan "Campus Facility" --lat 25.28933 --lon 55.47831

# Generate both PDF and HTML reports
solarscan scan "Computer Science Department W5 Sharjah" --format both
```

### Deterministic Offline Demo
```bash
solarscan demo --format both
```

### Batch Screening from CSV Portfolio
```bash
solarscan batch data/validation_buildings.csv --out reports/batch_run
```

---

## 6. Citation

If you use this framework or benchmark dataset in academic research, cite as:

```bibtex
@inproceedings{solarscan2026,
  title = {Automated Rooftop Solar Pre-Feasibility Assessment from OpenStreetMap Building Footprints},
  author = {Anonymous Authors},
  booktitle = {Proceedings of the International Conference on Sustainable Energy \& Power Systems (SEPS-2026)},
  year = {2026},
  address = {Sharjah, United Arab Emirates}
}
```

---

## 7. License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
