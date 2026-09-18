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
