# Automated Rooftop Solar Pre-Feasibility Assessment from OpenStreetMap Building Footprints

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Manuscript: PDF](https://img.shields.io/badge/Paper-PDF-red.svg)](manuscript/main.pdf)

Open-source Python framework (`solarscan`) and validation benchmark for automated rooftop solar pre-feasibility screening from crowdsourced OpenStreetMap (OSM) footprints.

## Key Findings

- **Multi-Building Benchmark ($N = 24$):** Evaluated against satellite imagery reference measurements across five UAE Emirates (Sharjah, Dubai, Abu Dhabi, Ajman, Ras Al Khaimah).
- **Geometric Agreement:** Mean Absolute Percentage Error (MAPE) of **4.54%**, Mean Bias Error (MBE) of **-4.54%**, and $R^2 = \mathbf{1.000}$.
- **Case Study (University of Sharjah W5):** 1,610.02 m² footprint area (94.72% agreement with ground truth), 272.38 kW DC array capacity, 260.33 MWh/yr yield, and 2.75-year simple payback.

## Quickstart

```bash
git clone https://github.com/IamOumarIbrahim/rooftop-scanning.git
cd rooftop-scanning
pip install -e .
```

Scan by address or GPS coordinates:
```bash
# Single building scan
solarscan scan "Computer Science Department W5 Sharjah" --format both

# Offline deterministic demo
solarscan demo --format both

# Batch screening from CSV
solarscan batch data/validation_buildings.csv --out reports/batch_run
```

Run test suite and reproducibility gate:
```bash
python scripts/gate_check.py
```

## Citation

```bibtex
@inproceedings{solarscan2026,
  title = {Automated Rooftop Solar Pre-Feasibility Assessment from OpenStreetMap Building Footprints},
  author = {Oumar Mamoun Ibrahim and Mohamad Khairi bin Ishak},
  booktitle = {Proceedings of the International Conference on Sustainable Energy \& Power Systems (SEPS-2026)},
  year = {2026},
  address = {Sharjah, United Arab Emirates}
}
```

## License

Distributed under the [MIT License](LICENSE).
