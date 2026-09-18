# AGENT.md — Rooftop Solar Pre-Feasibility Paper & Repository

> **CRITICAL DEADLINE:** Full paper submission for SEPS-2026 is **6 October 2026**.  
> Abstract registration closed 18 September 2026. Camera-ready and registration dates will be confirmed by the organisers.

Read this document before editing documentation, manuscripts, code, or figures.

---

## 1. Project Goal

Produce a complete, self-contained GitHub repository at  
https://github.com/IamOumarIbrahim/rooftop-scanning  

that contains:

1. A full conference-ready manuscript whose content is a **faithful expansion** of the submitted abstract (do not abandon or contradict it).
2. A clean, usable, fully reproducible Python codebase derived from the original SolarScan project (https://github.com/IamOumarIbrahim/solarscan-solar-analysis).
3. Gate-check verification scripts that prove every claim, equation, and numerical result in the paper can be regenerated from the repository alone.
4. This living `AGENT.md` file so any future agent or human can continue the work without loss of context.

### Submitted Abstract (non-negotiable core)

> Rooftop solar photovoltaic (PV) adoption often stalls at the point of first decision, when a business or property owner needs a fast, low-cost feasibility estimate before committing to an engineering study. Existing pre-feasibility methods, including manual satellite-image tracing, light detection and ranging (LiDAR) platforms, and paid application programming interfaces (APIs), are costly, proprietary, or unavailable across much of the United Arab Emirates, the Gulf, and the Global South. Unlike LiDAR platforms such as Google's Project Sunroof, which have little coverage in these regions, this work uses only free, crowdsourced OpenStreetMap (OSM) building-footprint data. This paper presents an open-source Python framework that generates automated rooftop solar feasibility reports from OSM data. Given an address or coordinate, the framework queries the OSM Overpass API for the building polygon, projects it into a local metric frame, and computes footprint area with the shoelace formula. It estimates roof azimuth, applies an irradiance derating factor, and models estimated annual energy yield.

---

## 2. Research Contribution Contract (Binding)

A reviewer must be able to answer "yes" to all of the following after reading the paper:

1. **The first-decision / pre-feasibility bottleneck is real and costly.** Initial engineering site surveys cost $1,000 to $5,000 and take weeks, causing property owners to abandon solar inquiries before evaluating feasibility.
2. **Existing solutions leave a documented gap in the UAE / Gulf / Global South.** Commercial platforms such as Google Project Sunroof and Google Solar API cover only select Western markets (primarily North America and parts of Europe), with zero coverage across the GCC and most of the Global South.
3. **This work is not "yet another OSM rooftop paper".** It is differentiated by a specific combination of properties that prior work does not simultaneously provide:
   - 100% open-source, local-first Python execution without proprietary GIS software (ArcGIS, QGIS).
   - Zero reliance on paid commercial APIs or LiDAR datasets.
   - End-to-end pipeline: from raw address or coordinate query to geometric extraction, usable area filtering, system sizing, POA irradiance derating, and simple payback economics.
   - Direct targeting and validation in a region (UAE/Gulf) where commercial solar data platforms are completely absent.
4. **The method is transparent, reproducible, and quantified against independent references.** Validated against an empirical ground-truth benchmark of 24 buildings across 5 Emirates in the UAE (Sharjah, Dubai, Abu Dhabi, Ajman, Ras Al Khaimah).
5. **The measured accuracy and limitations are stated honestly.** A practitioner knows exactly when the method is suitable (rapid first-pass screening on flat roofs, commercial portfolios) and when it is not (complex multi-pitch roofs, heavy local shading, structural engineering verification).

---

## 3. Style and Tone Guidelines (Hard Quality Gate)

Write in clear, direct Technical English:

- **Sentence structure:** Keep sentences short, simple, and active. Eliminate filler words.
- **Vocabulary:** Avoid overly complex or ornate vocabulary.
- **Acronyms:** Define every acronym upon its first appearance in the text.
- **Punctuation:** Do **not** use em dashes (—). Use hyphens (-), parentheses, or separate sentences instead.
- **Tone:** Zero promotional language. Avoid words such as "novel", "powerful", "state-of-the-art", "seamless", "revolutionary", or "unprecedented".
- **Evidence:** Prefer hard numbers, exact error metrics, and explicit limitations over subjective adjectives.
- **Logic:** Maintain strict logical progression of ideas across all sections.

---

## 4. Target Conference & Page Length

- **Conference:** International Conference on Sustainable Energy & Power Systems (SEPS-2026), University of Sharjah / University of Khorfakkan.
- **Official template:** IEEE conference format (`IEEEtran.cls` located in `manuscript/IEEEtran.cls`).
- **Compiled manuscript:** `manuscript/main.pdf` (9 pages, fully compiled with figures, tables, and references).
- **Target length:** 6 to 10 pages.

---

## 5. Repository Layout

```
rooftop-scanning/
├── AGENT.md                       # Agent and contributor execution log & quality contract
├── README.md                      # Project documentation and quickstart
├── LICENSE                        # MIT License
├── pyproject.toml                 # Packaging metadata
├── requirements.txt               # Dependency specifications
├── solarscan.yaml                 # Default regional sizing parameters
├── solarscan/                     # Core Python framework
│   ├── __init__.py
│   ├── cli.py
│   ├── geometry.py
│   ├── osm.py
│   ├── sizing.py
│   ├── yield_estimate.py
│   ├── fixtures.py
│   └── report.py
├── data/                          # Benchmark fixtures and dataset
│   ├── validation_buildings.csv   # Master 24-building empirical validation dataset
│   └── fixtures/                  # Deterministic OSM polygon JSON fixtures (26 buildings)
├── experiments/                   # Evaluation and figure generation scripts
│   ├── build_validation_dataset.py
│   ├── run_validation.py
│   ├── run_sensitivity.py
│   ├── generate_figures.py
│   └── generate_tables.py
├── manuscript/                    # Official IEEE conference manuscript
│   ├── main.tex                   # LaTeX manuscript source (IEEEtran format)
│   ├── references.bib             # Verified peer-reviewed bibliography
│   ├── IEEEtran.cls               # Official IEEE conference class
│   ├── IEEEtran.bst               # IEEE bibliography style
│   ├── main.pdf                   # Compiled 9-page conference manuscript
│   ├── figures/                   # Vector PDF and PNG publication figures
│   └── tables/                    # Modular LaTeX table inputs
├── tests/                         # Automated unit and integration tests (21 tests)
├── scripts/                       # Verification and automation scripts
│   ├── gate_check.py              # Automated 7-stage reproducibility quality gate
│   ├── reproduce_paper.bat        # Windows one-click paper reproduction script
│   └── reproduce_paper.sh         # Unix/Linux one-click paper reproduction script
└── reports/                       # Generated feasibility reports (PDF and HTML)
```

---

## 6. Exact Reproduction Commands

To reproduce all numerical metrics, figures, tables, and compile the final manuscript PDF from scratch:

```bash
# 1. Run full 7-stage automated quality gate check
python scripts/gate_check.py

# 2. Or run the complete reproduction script (Windows)
scripts\reproduce_paper.bat

# 2. Or run the complete reproduction script (Linux / macOS)
./scripts/reproduce_paper.sh
```

---

## 7. Current Project Status

- **Status:** Complete. All quality gates passed. Manuscript fully compiled (9 pages) in official IEEE template.
- **Last updated:** 2026-09-19
- **Automated Verification Summary:**
  - Unit & Integration Tests: 21/21 passed.
  - Multi-Building Validation: 24 buildings across 5 Emirates, MAPE = 4.54%, MBE = -4.54%, $R^2 = 1.000$, RMSE = 1,432.7 m².
  - Case Study (University of Sharjah W5): Area 1,610.02 m², 272.38 kW DC, 260.33 MWh/yr, 2.75-year payback.
  - Figures & Tables: All 7 figures and 5 tables generated from code (including single-column side-by-side satellite vs OSM trace comparison).
  - Style Quality Gate: 0 em dashes, 0 promotional adjectives, all acronyms defined on first use.
  - PDF Compilation: Compiled cleanly with `pdflatex` + `bibtex` (9 pages, 718.8 KB).


---

## 8. Pre-Submission Manual Checklist (Human Actions Required)

All automated engineering, benchmarking, style gates, and paper compilation are complete (100% gate pass). The remaining manual tasks requiring human review, credentials, or administrative decisions before submission to SEPS-2026 are:

1. **Authorship and Grant Status [Verified]:**  
   - 1st Author: Oumar Mamoun Ibrahim (Department of Computer Engineering, University of Sharjah, `U22200741@sharjah.ac.ae`).  
   - 2nd Author: Mohamad Khairi bin Ishak (Department of Computer Engineering, University of Sharjah, `mishak@sharjah.ac.ae`).  
   - Funding / Grant: Zero external funding or grant footnotes. (The `\IEEEoverridecommandlockouts` directive has been commented out).

2. **Review Mode Policy (Single-Blind vs Double-Blind):**  
   - Verify the SEPS-2026 submission guidelines on the conference portal (e.g. EDAS / Microsoft CMT).  
   - If the conference follows **single-blind review**, the current author block is ready as-is.  
   - If the conference requires **double-blind review**, temporarily mask the author block and institutional acknowledgments with anonymous placeholders for the initial review submission.

3. **Ground-Truth Building Blueprint Refinements (Optional):**  
   - Inspect `data/validation_buildings.csv` (24 buildings across 5 Emirates).  
   - If internal University of Sharjah facilities blueprints or CAD as-builts exist for Building W5 or M9, verify if you wish to adjust the satellite-derived reference area. Any update can be re-validated instantly with `python scripts/gate_check.py`.

4. **Institutional Literature Inclusion (Optional):**  
   - Review Section II (Related Work) and `manuscript/references.bib`.  
   - If there are recent published works by University of Sharjah or University of Khorfakkan colleagues in renewable energy / solar PV, citing them strengthens institutional alignment and reviewer resonance.

5. **Visual Inspection of the Compiled PDF (`manuscript/main.pdf`):**  
   - **Page Count:** Exactly 9 pages (target is 6–10 pages).
   - **Figures 1–6:** Verify readability of text annotations and contrast of color gradients in Figures 1, 2, 3, 4, 5, and 6.
   - **Typography & Formatting:** Ensure column balancing on page 9 and that all mathematical symbols render properly.

6. **IEEE PDF eXpress Compliance:**  
   - Check if SEPS-2026 requires IEEE PDF eXpress validation before portal upload. If required, upload `manuscript/main.pdf` to the conference's PDF eXpress portal using the conference ID to verify font embedding and PDF compatibility.

7. **Conference Portal Upload:**  
   - Submit `manuscript/main.pdf` to the SEPS-2026 management portal before the **6 October 2026** full paper deadline.