# Audit report (2026-11-08)

Every claim in the September 2026 version was re-checked twice: once with the repo's own code
and once with independent code or data (pyproj, Shapely/UTM, PVGIS, pvlib, Crossref,
Microsoft footprints, live OSM).

## 1. What was wrong

| # | Severity | Problem | How it was found | Status |
|---|---|---|---|---|
| 1 | Critical | 23 of 24 "Google Earth" reference areas were never traced. Only JAFZA had evidence. MAPE 4.54 %, MBE −4.54 %, R² = 1.000 and the per-type table all came from these values. | No trace files. ref/OSM = 1.048 ± 0.007 across a 1,600× size range. Microsoft footprints disagree by −79 % to +92 %. Author confirmed. | Removed. Replaced by Microsoft comparison + manual-trace kit. |
| 2 | Critical | W5 azimuth 68.2° typed by hand in tables, figures and gate check. The code gives 303.78° (or 123.78° with reversed vertices). | Ran the code. Reversed the polygon. | Fixed: axis from minimum rotated rectangle, independent of vertex order. |
| 3 | Critical | Paper yield 260.33 MWh and payback 2.75 yr did not match the paper's own CLI (232.39 MWh, 3.08 yr). | `solarscan demo` | Fixed: all numbers generated. |
| 4 | High | Orientation derate `cos(Δψ/2)·cos(|β−20|/2)` was invented. East at 15°: 70.6 % (PVGIS 88.4 %). Flat panels changed with azimuth (impossible). | PVGIS API + pvlib | Replaced by stored PVGIS grids (pvlib agrees within 1.8 %). |
| 5 | High | Panels were treated as facing along a wall (a line bearing), not perpendicular to it. | Geometry | Fixed: rows face south by default (NREL flat-roof rule). |
| 6 | High | Cost "$1,000/kW" in methods, "1,000 AED/kW" in results. Market price is about 2,800–4,000 AED/kWp. Payback 2.75 yr was too optimistic. | Units check, installer quotes | 3,000 AED/kWp default, 2,500–4,000 range shown. |
| 7 | High | Modules covered 100 % of the usable roof (no row spacing). | NREL flat-roof assumptions | Packing factor 0.70 added. |
| 8 | High | 13 of 21 references were wrong: 9 real papers with wrong DOI, year or authors (DeepSolar's author list was invented), 4 not found at all. | Crossref by DOI, then by title | Rebuilt. 20/20 DOIs verified by `scripts/check_references.py`. |
| 9 | Medium | On network failure the OSM client returned a synthetic 33 m square. Failed geocoding silently returned University of Sharjah coordinates. | Code reading | Both now raise errors. Tests added. |
| 10 | Medium | Building names were embellished ("RAK Mall" was an unnamed 934 m² building; a "logistics depot" was a car-repair shop; an "annex" was tagged `house`). | Live OSM tags | Names now follow OSM tags. |
| 11 | Medium | "< 0.01 % projection distortion" was false: the spherical radius added ~0.2 % to every area. | pyproj geodesic area | Ellipsoidal radii: max error 0.0004 %. |
| 12 | Medium | Steiner πs² corner term stated for inward offsets (wrong) and claimed "strictly conservative" for non-convex roofs (false). | Geometry | Exact polygon buffer used. Claim removed. |
| 13 | Medium | R² = 1.000 reported as evidence of accuracy. With areas from 124 to 200,000 m², R² ≈ 1 for almost any method. | Statistics | Removed. Median and MAPE reported. |
| 14 | Low | "≥ 1,000 m² buildings" included 124 m² and 934 m² buildings. "Google Solar API has zero UAE coverage" was not verifiable. | Data, web | Claims corrected or removed. |
| 15 | Low | Gate check and tests asserted the fabricated numbers, so they could never catch an error. | Code reading | Replaced by regenerate-and-diff (`reproduce.py --verify`). |
| 16 | Low | Invented helper models (clipping loss `75·(ILR−1.15)²`, PR breakdown) shipped as API. | Code reading | Removed. |
| 17 | Low | Clutter: 66 KB fake "20-pass review" log, scratch images, copied IEEE template, 24 unused fixtures, 7k-line raw dump. | — | Removed. |

## 2. Highest-ROI changes (done)

| Change | Why it matters |
|---|---|
| Numbers-as-code (`numbers.tex` macros + checker) | The paper can no longer disagree with the code. |
| Real, released reference polygons (Microsoft) + blind manual-trace kit | Validation is honest and anyone can repeat it. |
| PVGIS yield grids + pvlib cross-check | Yield now rests on measured irradiance, verified by a second model. |
| Sensitivity (tornado) instead of one point estimate | Shows payback is 3.9–6.2 yr and driven by cost and tariff, not roof shape. |
| Byte-identical regeneration + CI `--verify` | Reviewers can check every figure and number in one command. |

| Module-by-module layout replaces the bare packing factor | The 0.70 rule overestimated W5 by 10 % and small roofs by up to 36 %. Now tested on all 24 roofs. |
| Real satellite imagery and a Blender render in the figures | Readers see the roof, the OSM error and the module rows, not abstract plots. Georeferencing was checked: the hand traces sit on the roof edges. |

## 3. Still to do (by the authors)

1. (Done) The image check first rejected 12 traces. The cause was the overlay, not the traces: Google Maps
   draws fractional zoom levels at a different scale than the URL states. Images are now taken at whole
   zoom levels, and all 24 traces sit on the roof edge. Re-check the OSM labels if you change a trace.
2. (Done) Tariff 0.38 AED/kWh is the top DEWA/SEWA slab; the fuel surcharge (about 0.06) and VAT are not
   included, so the default is conservative. 3,000 AED/kWp matches installer prices for systems above
   about 15 kWp. The sensitivity range (tariff +0.06, cost -500/+1,000) covers both.
3. If the old version was submitted, tell the programme chairs that the validation data changed.
