# Contributing to Rooftop-Scanning & SolarScan

Thank you for your interest in contributing to the Rooftop-Scanning open-source pre-feasibility research framework!

## Research Mission
This repository provides a 100% reproducible, open-access, local-first framework to estimate rooftop solar PV potential in regions lacking commercial LiDAR coverage (UAE, GCC, and the Global South).

## How to Contribute

### 1. Contributing Ground-Truth Benchmark Buildings
To add ground-truth building polygons from your region:
1. Locate the building on OpenStreetMap to obtain the OSM Way ID or node coordinates.
2. Measure the outer parapet rooftop perimeter in Google Earth Pro or calibrated municipal orthoimagery at sub-meter resolution.
3. Save the OSM Overpass JSON polygon response in `data/fixtures/<building_id>.json`.
4. Append the record to `data/validation_buildings.csv`.
5. Run `python experiments/run_validation.py` to regenerate summary statistics.

### 2. Code Quality & Standards
- Code must follow PEP 8 style standards with type hints where appropriate.
- Every new feature must be accompanied by unit tests under `tests/`.
- No proprietary GIS software (ArcGIS, QGIS) or paid commercial APIs may be introduced as mandatory dependencies.

### 3. Verification
Before opening a pull request, ensure all tests pass:
```bash
pytest -v tests/
python scripts/gate_check.py
```
