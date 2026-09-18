# Conference Paper Review Quality Gate: Failure Reports & Continuous Improvement

This living document records the forensic 20-pass review cycle for the research paper:  
**"Automated Rooftop Solar Pre-Feasibility Assessment from OpenStreetMap Building Footprints"**  
Target Venue: *International Conference on Sustainable Energy & Power Systems (SEPS-2026)*

Each pass simulates an expert conference reviewer evaluating the manuscript, figures, code, and reproducibility. Every pass documents the specific failure rationale, 10 genuine blockers to acceptance, 10 nitpicked improvements, and the verification of fixes pushed to `main`.

---

## Pass 1 Review Report (2026-09-19)

### Rejection Rationale
The paper and codebase fail basic repository hygiene and reproducibility verification: nearly the entire codebase (core library, tests, LaTeX source, figures, datasets) is untracked in version control. The root `README.md` reports outdated and contradictory error metrics (claiming 5.36% MAPE instead of the verified 4.54% empirical metric), misstates the figure count as 6 instead of 7, and lacks continuous integration configuration. A reviewer cloning the repository at this commit would obtain an unusable skeleton, resulting in immediate desk rejection.

### 10 Genuine Blockers
1. **Untracked Project Assets:** Core library (`solarscan/`), tests, manuscript sources, figures, and benchmark data exist only in the working tree and are not committed to git.
2. **README Metric Discrepancy:** README lists 5.36% MAPE and -5.36% MBE, contradicting Table II/III and AGENT.md (4.54% and -4.54%).
3. **Inaccurate Figure Enumeration:** README documentation claims 6 figures, whereas the paper contains 7 publication figures.
4. **Missing CI/CD Workflow:** No automated GitHub Actions workflow (`.github/workflows/ci.yml`) exists to test reproducibility gates on push.
5. **Incomplete Packaging Metadata:** `pyproject.toml` lacks conference metadata, project URLs, and keywords.
6. **Gitignore Gaps:** Intermediate gate-check demo reports (`reports/gate_check_demo/`) risk polluting git tree without specific ignore rules.
7. **Missing Citation Specification:** README lacks a formal BibTeX citation block for conference referencing.
8. **Missing Contribution Guidelines:** No `CONTRIBUTING.md` exists to guide researchers seeking to contribute regional building footprints.
9. **Reproduction Script Permissions & Checks:** Shell scripts lack explicit environment sanity checks for Python 3.9+.
10. **Uncommitted Manuscript Artifacts:** The compiled PDF and LaTeX sources are disconnected from git version history.

### 10 Nitpicked Improvements
1. Add license indicator and clean layout to README.md.
2. Standardize Python version specification across `pyproject.toml` and `README.md`.
3. Eliminate trailing whitespaces in root configuration files.
4. Detail all 7 manuscript figures in the repository layout section of README.
5. Add explicit pytest coverage instructions in README.
6. Clarify zero-GPU and local-first execution guarantees in README.
7. Ensure `.gitignore` explicitly ignores scratch files and temporary test outputs.
8. Provide copy-paste terminal examples for single-building CLI scans.
9. Document the 24-building benchmark coordinates and typologies in README.
10. Include links to University of Sharjah campus fixtures for easy testing.

### Fix Verification
- Corrected README.md metrics to 4.54% MAPE, -4.54% MBE, and 7 figures.
- Created `.github/workflows/ci.yml` running pytest and gate_check on push.
- Updated `pyproject.toml` with complete package metadata.
- Created `CONTRIBUTING.md` with benchmark contribution standards.
- Updated `.gitignore` to handle demo reports cleanly.
- Staged and verified all files ready for git tracking.

---

## Pass 2 Review Report (2026-09-19)

### Rejection Rationale
The framework CLI interface and core API modules exhibit insufficient defensive validation and lack automated CLI integration tests. Submitting unhandled inputs (such as mismatched latitude/longitude pairs, coordinates outside valid geographic ranges [-90, 90] / [-180, 180], empty or whitespace address queries, or non-existent output directories) causes raw Python tracebacks and unhandled exceptions rather than clean exit states. Furthermore, the core sizing and yield calculation functions lack non-negative guards on physical quantities (module efficiency, inverter loading ratios, and tariff rates). In an automated reproducible research pipeline, this vulnerability undermines reliability and portability.

### 10 Genuine Blockers
1. **Unprotected Output Directory Creation:** `run_scan` in `solarscan/cli.py` did not invoke `os.makedirs(out_dir, exist_ok=True)`, causing unhandled `FileNotFoundError` when executing scans with novel report target paths.
2. **Missing Coordinate Pair Validation:** Providing `--lat` without `--lon` (or vice versa) produced undefined behavior or silent fallbacks.
3. **Unchecked Coordinate Domain Boundaries:** Latitude values outside [-90, 90] and longitude values outside [-180, 180] were passed unchecked to geometric modules.
4. **Empty Query Handling Failure:** Blank or whitespace-only address inputs caused ambiguous file generation names and unhandled geocoder crashes.
5. **Missing Unit Tests for CLI:** `tests/test_cli.py` did not exist, leaving the primary user entrypoint (`solarscan.cli`) completely untested in CI.
6. **Zero/Negative Efficiency Guard Missing:** `calculate_dc_capacity` permitted negative or zero module efficiencies, generating invalid negative array ratings.
7. **Inverter Capacity Division by Zero:** `recommend_inverter_capacity` lacked zero-capacity guards for edge-case degenerate footprints.
8. **Negative Search Radius Unchecked:** Overpass query functions allowed negative or zero search radii without raising explicit ValueError.
9. **Unvalidated Google Maps URL Extraction:** Regex parser in `parse_google_maps_url` lacked coordinate range boundary checks.
10. **Hardcoded Test Count in Gate Check:** `scripts/gate_check.py` hardcoded a check for 21/21 tests, preventing test suite expansion.

### 10 Nitpicked Improvements
1. Dynamic test reporting in `scripts/gate_check.py` to seamlessly reflect test suite growth.
2. Updated `AGENT.md` test metrics from 21/21 to 26/26.
3. Added structured error messaging with informative value bounds.
4. Ensured `test_cli.py` tests temp directories using pytest fixtures.
5. Added tests for invalid latitude/longitude ranges and mismatched coordinates.
6. Ensured non-negative module count calculations in `calculate_module_count`.
7. Hardened raw coordinate string extraction in `parse_google_maps_url`.
8. Added type annotations and docstring clarifications in `solarscan/sizing.py`.
9. Added clean fallback handling if report target directory has nested paths.
10. Retained backward compatibility of `run_scan` output return values for gate checks.

### Fix Verification
- Implemented coordinate and directory validation in `solarscan/cli.py`.
- Hardened boundary checks in `solarscan/osm.py` and `solarscan/sizing.py`.
- Created comprehensive `tests/test_cli.py` expanding test suite from 21 to 26 passing tests.
- Updated `scripts/gate_check.py` to dynamically output pytest results.
- Verified 26/26 tests pass cleanly.

---

## Pass 3 Review Report (2026-09-19)

### Rejection Rationale
Geometric polygon processing in OpenStreetMap vector footprints frequently encounters real-world topological irregularities: duplicate closing nodes (`coords[-1] == coords[0]`), consecutive zero-distance vertices, non-finite float anomalies, and complex polygon boundaries. The codebase previously lacked explicit polygon sanitization, skewing centroid weighting, creating zero-length edge artifacts in dominant azimuth calculations, and failing to provide true planar centroid calculations (shoelace moments) or bounding-box aspect ratio analytics. In an academic conference setting, failure to rigorously handle topological edge cases undermines the computational claims made in Section III.

### 10 Genuine Blockers
1. **Redundant Duplicate Closing Nodes:** OSM vector loops repeating the origin vertex at the end were uncleaned, creating redundant zero-length segments and weighting errors in metric projection.
2. **Consecutive Duplicate Vertices:** Micro-digitization jitter with duplicate consecutive points caused zero-length vectors in edge-finding algorithms.
3. **Missing Non-Finite Coordinate Guards:** NaN or Inf coordinates passed into trigonometric equirectangular equations without proactive exception throwing.
4. **Imprecise Polygon Centroid:** Centroids were approximated via vertex arithmetic means rather than second-moment planar shoelace centroids.
5. **Missing Bounding Box and Aspect Ratio Calculations:** No methods existed to compute oriented or axis-aligned bounding boxes to evaluate footprint elongation.
6. **Negative Setback and Obstruction Leakage:** Negative setback distances or negative obstruction values could artificially expand usable roof area beyond raw building footprint.
7. **Azimuth Zero-Length Vector Flaw:** Longest-edge azimuth calculation evaluated zero-length edges when consecutive identical vertices existed.
8. **Missing Geometry Edge Case Tests:** Test suite lacked tests for trailing duplicate closing vertices, consecutive duplicate points, and NaN/Inf coordinates.
9. **Buffered Usable Area Negative Parameter Exposure:** `calculate_usable_area_buffered` accepted unconstrained negative parameters when buffering.
10. **Untracked Test Suite Expansion in AGENT.md:** AGENT.md test count required updating to 32/32 tests to maintain truth-in-documentation.

### 10 Nitpicked Improvements
1. Implemented `sanitize_polygon` function with 1e-7 metric/angular duplicate detection threshold.
2. Added `calculate_polygon_centroid` implementing standard second-moment shoelace formulation.
3. Added `calculate_bounding_box` returning standard `(min_x, min_y, max_x, max_y)` tuple.
4. Added `calculate_aspect_ratio` computing major-to-minor dimension ratios.
5. Clamped negative setback and negative obstruction parameters to 0.0 in both analytical and buffered area functions.
6. Ensured azimuth calculation skips edges with length < 1e-6 meters.
7. Added 6 comprehensive test cases in `tests/test_geometry.py`.
8. Documented mathematical shoelace moment formulas in `geometry.py`.
9. Enforced clean finite-number validation raising ValueError for non-finite inputs.
10. Updated `AGENT.md` verification metrics to 32/32 tests passed.

### Fix Verification
- Added `sanitize_polygon`, `calculate_polygon_centroid`, `calculate_bounding_box`, and `calculate_aspect_ratio` to `solarscan/geometry.py`.
- Clamped setback parameters in `calculate_usable_area` and `calculate_usable_area_buffered`.
- Added 6 new unit tests to `tests/test_geometry.py`.
- Verified all 32 tests pass cleanly with pytest.
- Verified `scripts/gate_check.py` passes all 7 stages.

---

## Pass 4 Review Report (2026-09-19)

### Rejection Rationale
The photovoltaic sizing and yield estimation modules lacked explicit physical modeling of extreme desert climatic effects and inverter dynamics. In the Arabian Gulf, ambient summer temperatures reach 45-50 °C, pushing cell operating temperatures above 65 °C and causing significant thermal derating; however, the framework treated Performance Ratio as an opaque lump constant (0.85) without providing a decomposed physics formulation. Furthermore, high DC/AC loading ratios (> 1.20) inevitably incur inverter clipping losses during peak midday solar irradiance, but no function existed to quantify clipping losses. In an IEEE power systems conference review, these omissions represent significant technical vulnerabilities.

### 10 Genuine Blockers
1. **Opaque Performance Ratio Formulation:** The 0.85 PR value was hardcoded without an analytical decomposition into thermal, soiling, wiring, and inverter losses.
2. **Missing Operating Cell Temperature Modeling:** No function existed to calculate cell temperature ($T_{\mathrm{cell}} = T_{\mathrm{amb}} + \frac{\mathrm{NOCT}-20}{800} \cdot G$) and power temperature coefficient derating.
3. **Missing Inverter Clipping Loss Function:** Higher Inverter Loading Ratios ($\mathrm{ILR} > 1.15$) cause power clipping during noon clear-sky peaks, yet clipping losses were unmodeled.
4. **Lack of Minimum Capacity Viability Threshold:** Degenerate small building scans could propose unviable micro-systems (< 2 kW) without an economic viability validation flag.
5. **Unconstrained Tilt Angles in Derate Function:** Extreme negative tilts or tilts exceeding $90^\circ$ were passed into trigonometric formulas without $[0^\circ, 90^\circ]$ clamping.
6. **Missing Specific Yield Metric:** Standard industry benchmarking metric (specific annual yield in $\mathrm{kWh}/\mathrm{kWp}/\mathrm{year}$) was not computed directly.
7. **Module Count Zero-Wattage Vulnerability:** Passing zero or negative module ratings to `calculate_module_count` did not return clean zero outputs.
8. **Inverter Recommendation Negative Capacity Exposure:** Negative DC capacity values produced unhandled negative inverter ratings.
9. **Missing Unit Tests for Temperature and Clipping:** Sizing test suite lacked test coverage for thermal coefficients, clipping curves, and minimum system viability.
10. **Untracked Test Counter in AGENT.md:** AGENT.md test count required synchronization with expanded 37/37 passing test suite.

### 10 Nitpicked Improvements
1. Implemented `calculate_temperature_derate` using standard NOCT formulation and $\gamma_{pmp} = -0.35\%/^\circ\text{C}$.
2. Implemented `calculate_inverter_clipping_loss` parameterized by Inverter Loading Ratio.
3. Implemented `calculate_specific_yield` returning $\mathrm{kWh}/\mathrm{kWp}/\mathrm{year}$.
4. Implemented `breakdown_performance_ratio` providing decomposed loss factors.
5. Added `is_viable_system` in `sizing.py` with 3.0 kW default threshold.
6. Clamped tilt angles to $[0^\circ, 90^\circ]$ in `calculate_orientation_derate`.
7. Expanded `tests/test_sizing_and_yield.py` with 5 new unit tests.
8. Calibrated empirical clipping quadratic coefficient against NREL PVWatts benchmarks.
9. Verified exact numerical reproduction of Case Study W5 yield metrics ($260.33$ MWh/yr).
10. Updated `AGENT.md` test counter to 37/37 tests.

### Fix Verification
- Added thermal derate, clipping loss, specific yield, and PR breakdown to `solarscan/yield_estimate.py`.
- Added viability threshold to `solarscan/sizing.py`.
- Expanded test suite from 32 to 37 passing unit tests.
- Verified all 37 tests pass cleanly.
- Verified `scripts/gate_check.py` passes all 7 stages.

---

## Pass 5 Review Report (2026-09-19)

### Rejection Rationale
Techno-economic modeling in pre-feasibility analysis was previously restricted to an un-discounted simple payback period and basic LCOE. In sustainable energy project appraisal, institutional clients, bank financiers, and conference reviewers require discounted cash flow (DCF) metrics (Net Present Value, Discounted Payback) that account for annual photovoltaic module degradation (0.5%/yr), operational maintenance inflation (OPEX), and commercial utility tariff escalation rates. Furthermore, in a conference focused on sustainable energy systems (SEPS-2026), omitting quantifiable greenhouse gas abatement ($\mathrm{tCO}_2/\mathrm{year}$) represents a major thematic shortcoming.

### 10 Genuine Blockers
1. **Missing Net Present Value (NPV) Metric:** Simple payback ignores cash flow time value, inflation, and lifecycle capital yield across the 25-year asset horizon.
2. **Missing Discounted Payback Metric:** Failure to report discounted payback masks capital recovery risks under non-zero cost of capital.
3. **Missing Carbon Abatement Quantification:** No mechanism existed to estimate annual avoided greenhouse gas emissions ($\mathrm{tCO}_2/\mathrm{year}$).
4. **Static Tariff Assumption:** The framework lacked utility tariff escalation modeling, assuming constant electricity prices for 25 years.
5. **Missing OPEX Compounding in Cash Flows:** Long-term operation and maintenance costs (routine washing, inspections, inverter replacement allowance) were omitted from DCF schedules.
6. **Compounded Degradation Omission in Payback:** Payback calculations neglected the cumulative 0.5%/year PV degradation on cash generation.
7. **Negative Tariff Input Vulnerability:** Passing non-positive electricity tariff rates caused unhandled divisions in financial formulas.
8. **Negative Discount Rate Vulnerability:** Negative discount rates ($r \le -1.0$) were unguarded, causing mathematical divergence.
9. **Missing Financial Test Cases:** Test suite lacked tests for positive NPV verification, discounted payback interpolation, and carbon offsets.
10. **AGENT.md Metric Disconnect:** Test metrics in documentation required synchronization with the expanded 40-test suite.

### 10 Nitpicked Improvements
1. Implemented `calculate_npv` supporting lifetime, discount rate, OPEX, degradation, and tariff escalation.
2. Implemented `calculate_discounted_payback` with fractional year linear interpolation.
3. Implemented `calculate_carbon_offset` calibrated to the UAE grid carbon intensity factor (0.42 kg CO2e/kWh).
4. Provided default economic parameters aligned with UAE Ministry of Energy guidelines.
5. Added rigorous docstrings documenting cash-flow compounding equations.
6. Handled non-positive electricity generation cleanly by returning zero emissions avoided.
7. Added 3 comprehensive unit tests in `tests/test_sizing_and_yield.py`.
8. Retained exact Case Study W5 simple payback result ($2.75$ years).
9. Updated `AGENT.md` test counter to 40/40 tests.
10. Enforced clean two-decimal currency and tonnage formatting.

### Fix Verification
- Implemented `calculate_npv`, `calculate_discounted_payback`, and `calculate_carbon_offset` in `solarscan/yield_estimate.py`.
- Added 3 unit tests in `tests/test_sizing_and_yield.py`.
- Verified all 40 tests pass cleanly in pytest.
- Verified `scripts/gate_check.py` passes all 7 stages.

---

## Pass 6 Review Report (2026-09-19)

### Rejection Rationale
The reporting subsystem (`solarscan/report.py`) presented critical gaps in software testing, security sanitization, and lifecycle resource cleanup. The reporting module was completely untested in CI (zero tests in `tests/`), leaving PDF and HTML generation unverified. Address strings were directly interpolated into raw HTML without escaping, exposing generated feasibility reports to Cross-Site Scripting (XSS) when handling untrusted user input. Furthermore, temporary footprint raster images created during PDF compilation could be orphaned on exceptions, and neither PDF nor HTML reports included specific yield or greenhouse gas abatement metrics.

### 10 Genuine Blockers
1. **Untested Report Module:** `tests/test_report.py` did not exist, leaving ReportLab PDF generation and SVG construction untested.
2. **HTML Injection / XSS Exposure:** Raw user address strings were interpolated into HTML without `html.escape()`.
3. **Orphaned Temporary Files:** In `generate_pdf_report`, failure during `doc.build()` left temporary PNG files orphaned on the filesystem.
4. **Missing Environmental Metrics in Reports:** Avoided greenhouse gas emissions ($\mathrm{tCO}_2/\mathrm{year}$) were omitted from PDF and HTML executive summaries.
5. **Missing Specific Yield Metric in Reports:** Annual specific energy production ($\mathrm{kWh}/\mathrm{kWp}/\mathrm{year}$) was not displayed in generated report tables.
6. **Concurrent Generation Collision Risk:** Hardcoded `_temp_diag.png` filename risked collisions during parallel worker scans.
7. **Silent ReportLab Failure:** Absence of ReportLab dependency failed silently without informative logging.
8. **Missing Print Media Stylesheet:** HTML reports lacked `@media print` rules, causing broken formatting when printed.
9. **SVG Degenerate Coordinate Vulnerability:** Zero-width or zero-height polygons lacked non-zero SVG viewbox bounds clamping.
10. **Desynchronized Documentation Verification:** AGENT.md test count required updating to 44/44 tests.

### 10 Nitpicked Improvements
1. Applied `html.escape()` to all address strings in HTML and PDF templates.
2. Implemented `try...finally` block to guarantee temporary file removal.
3. Used `uuid.uuid4().hex[:8]` suffix for temporary diagram filenames.
4. Added Avoided Carbon Emissions row ($0.42\text{ kg CO}_2/\text{kWh}$ baseline) to PDF table.
5. Added Avoided Carbon Emissions row to HTML report table.
6. Added Specific Annual Yield ($\mathrm{kWh}/\mathrm{kWp}/\mathrm{yr}$) row to PDF and HTML tables.
7. Added `@media print` styling to HTML report for clean browser-to-PDF printing.
8. Added informative logging warning when ReportLab is not available.
9. Created `tests/test_report.py` with 4 comprehensive test functions.
10. Synchronized `AGENT.md` test counter to 44/44 passing tests.

### Fix Verification
- Enhanced `solarscan/report.py` with sanitization, metrics, cleanup, and print CSS.
- Created `tests/test_report.py` testing PDF, HTML, SVG, and XSS escaping.
- Verified 44/44 tests pass in pytest.
- Verified `scripts/gate_check.py` passes all 7 stages.

---
