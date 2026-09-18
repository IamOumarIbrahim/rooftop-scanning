# Systematic Prior-Art Search & Gap Analysis

## 1. Literature Search Protocol

- **Databases Queried:** IEEE Xplore, ACM Digital Library, Scopus / ScienceDirect, arXiv, Google Scholar.
- **Search Terms Combinations:**
  - `(rooftop solar OR PV potential OR pre-feasibility) AND (OpenStreetMap OR OSM OR Overpass)`
  - `(rooftop solar) AND (LiDAR OR Project Sunroof OR Google Solar API) AND (coverage OR Global South OR Middle East)`
  - `(building footprint) AND (rooftop PV) AND (validation OR accuracy OR MAPE)`
  - `(United Arab Emirates OR UAE OR Dubai OR Sharjah) AND (rooftop solar potential OR GIS)`

---

## 2. Comparative Prior-Art Matrix

| Study / Tool | Core Data Source | Open Source & Reproducible | Geographic Focus & Coverage | End-to-End Pipeline (Area -> Sizing -> Yield -> Payback) | Key Limitations for First-Decision Screening |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Project Sunroof** (Trehan et al.) | Aerial LiDAR + 3D mesh | No (Proprietary Google service) | US & Germany only (0% coverage in UAE / GCC / Global South) | Yes (Consumer-oriented) | Completely unavailable in target regions; proprietary black-box algorithms. |
| **Google Solar API** (Commercial API) | High-res satellite + AI | No (Paid commercial API, proprietary) | ~40 countries (Western Europe, US, Japan; 0% GCC coverage) | Partial (Outputs raw geometry & potential; requires custom billing integration) | Paywalled; unavailable in UAE/GCC; black-box neural networks. |
| **Assouline et al. (2017)** *Appl. Energy* | GIS cadastre + Random Forests | No (Methodological paper, proprietary data) | Switzerland | No (City-scale gross technical potential, no single-site sizing/payback) | Requires national LiDAR/cadastre; complex ML stack; no real-time address query. |
| **Mainzer et al. (2017)** *Solar Energy* | OpenStreetMap + aerial imagery | No code released | Germany (municipal scale) | No (Focuses on regional roof slope distribution) | Tailored to pitched European roofs; no automated single-building screening tool. |
| **Walch et al. (2020)** *Appl. Energy* | 3D building models (LoD2) + LiDAR | Code partial (R/Python scripts, open data repo) | Switzerland | No (Statistical hourly potential aggregation) | Requires high-density LoD2 CityGML, non-existent in developing regions. |
| **Rees et al. (2025)** *ISPRS IJGI* | Airborne LiDAR + OSM | Open data / QGIS workflow | Tromsø, Norway | No (Geospatial solar irradiance mapping) | Requires airborne LiDAR flights; dependent on desktop GIS software (QGIS). |
| **Gassar & Cha (2021)** *Build. Environ.* | Systematic Review | N/A (Review) | Global review | N/A | Documents that >85% of literature relies on data unavailable in developing countries. |
| **Alhammami & An (2021)** *Renew. Energy* | PVsyst + municipal survey | No open tool | Abu Dhabi, UAE | Yes (Techno-economic focus) | Manual single-site PVsyst modeling; no automated spatial screening or code. |
| **Hamdi (2024)** *IEEE Access* | Policy / macro statistics | N/A | Dubai & Abu Dhabi, UAE | No (Regulatory and policy evaluation) | Macro policy focus; provides no building-level assessment tool. |
| **pvlib-python** (Holmgren et al.) | Python library | Yes (BSD-3) | Global (Weather-dependent) | Partial (Physics engine only; no building footprint/spatial extraction) | Requires user to supply exact tilt, azimuth, area, and module parameters. |
| **PyPVRoof / SolarPowerRoofTop** | LoD2 3D models / satellite | Yes (Open source) | Select European cities | No (Focus on orientation/tilt extraction) | Requires 3D LoD2 city models or deep learning satellite pipelines. |
| **This Work (SolarScan Framework)** | **Free crowdsourced OpenStreetMap (Overpass API)** | **Yes (100% open source, zero external API keys)** | **Demonstrated & validated in UAE / GCC / Global South** | **Yes (Address -> OSM footprint -> shoelace area -> setback -> DC capacity -> derated yield -> payback)** | **Flat-roof assumption (predominant in GCC); relies on OSM footprint quality.** |

---

## 3. The Gap Statement

> **Documented Gap Statement:**  
> Existing commercial rooftop solar feasibility services (such as Google Project Sunroof and the Google Solar API) rely on proprietary airborne LiDAR and high-resolution aerial photogrammetry, restricting their availability almost exclusively to North America, Western Europe, and select OECD nations. Across the United Arab Emirates, the wider Arabian Gulf, and the Global South, these commercial platforms have zero coverage. Concurrently, academic literature on GIS-based solar potential is heavily concentrated on European and North American cities, assuming access to municipal cadastres, airborne laser scanning, or 3D CityGML models that do not exist or are strictly restricted in developing and emerging economies. While open tools such as pvlib model PV physics with high fidelity, they require pre-determined physical geometries and offer no spatial extraction capability. Prior OpenStreetMap-based studies have focused primarily on regional macro-aggregations in Europe, leaving an unaddressed gap: there is no lightweight, open-source, local-first framework that converts raw street addresses or geographical coordinates directly into end-to-end solar pre-feasibility reports using only freely accessible global vector data, whose geometric fidelity and yield predictions are quantitatively benchmarked in a commercial coverage-gap region.

---

## 4. Exact Contribution Claims

This paper makes the following specific contributions:
1. **Targeted End-to-End Open Framework:** An open-source Python framework that couples the OpenStreetMap Overpass API, local metric transverse projection, shoelace polygonal geometry, perimeter setback buffering, dominant edge azimuth extraction, empirical irradiance derating, and simple payback economics into a single execution command requiring no API keys, GPUs, or commercial GIS licenses.
2. **Empirical Ground-Truth Validation in a Coverage Gap Region:** A multi-building empirical validation across 20+ diverse buildings in the United Arab Emirates (Sharjah, Dubai, Abu Dhabi, Ajman, Ras Al Khaimah), comparing automated OSM footprints against high-resolution satellite ground-truth measurements across institutional, commercial, industrial, and residential building typologies.
3. **Quantified Error and Sensitivity Bounds:** Rigorous statistical evaluation reporting Mean Absolute Percentage Error (MAPE), Mean Bias Error (MBE), and Root Mean Square Error (RMSE), accompanied by parametric sensitivity analyses of setback distances and orientation deratings, establishing explicit boundaries for when OSM-based screening is reliable for first-decision feasibility.
