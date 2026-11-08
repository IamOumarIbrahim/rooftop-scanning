# Manual reference traces

This folder holds the manual roof traces that serve as ground truth for the area validation.
The pipeline reads only what is stored here. No reference number is typed by hand anywhere else.

## How to trace one building (about 4 minutes)

1. Run `python experiments/export_trace_kml.py` once. It writes one pin per building to `_to_trace/`.
2. Open `_to_trace/<id>.kml` in **Google Earth Pro** (desktop). It flies to the building.
   The file shows a pin only, not the OSM outline. Do not open OpenStreetMap while tracing.
3. Set *View → Historical Imagery* to the newest image. Write down its date.
4. Click **Add → Polygon**. Click around the **outer edge of the roof (parapet)**.
   Zoom in so each click lands within about 0.5 m of the edge. Skip canopies that are not part of the roof.
5. Name the polygon `<id>` (for example `uos_w5`). In the *Description* box, write `imagery: YYYY-MM-DD`.
6. Right-click the polygon in *Places* → **Save Place As…** → KML (not KMZ) → save as `data/reference_traces/<id>.kml`.
7. Run `python scripts/reproduce.py`. The dataset, metrics, figures, tables and paper update automatically.

## One file for all traces (easiest)

You can draw every polygon in one Google Earth folder and save it once as `manual_traces.kml`.
The analysis reads every polygon in that file and matches it to a building by its name.
Pins (points) in the file are ignored.

## Image check (required)

Run `python experiments/review_traces.py` and look at every image in `_review/`. Set each building to `pass`
in `trace_qc.csv` only if the orange trace follows the roof edge (no yards, parking, streets or neighbors).
Only `pass` traces are used in the paper.

The overlay is only correct if the image scale is known. `fetch_imagery.py` therefore requests whole
zoom levels only: Google Maps draws a fractional zoom (for example 19.49) at a different scale than the
URL states, and an earlier version of this check drew the outlines up to 1.9 times too large. If an
overlay looks too large or shifted for *both* outlines, suspect the image, not the trace.

## OSM status

After tracing, record in `osm_assessment.csv` whether each OSM outline is correct, and if not, why:
`partial`, `ground_as_roof`, `courtyard_as_roof` or `multi_level`.

## Rules

- One polygon per file. The file name must match the building `id` in `data/buildings.csv`.
- Trace from imagery only. Never copy or snap to the OSM outline.
- If the roof is not visible (clouds, blur, building demolished), do not trace it. Add a row to
  `excluded.csv` with the reason.

## Other sources

`manual_measurements.csv` holds measurements that exist only as a screenshot, not as a polygon
(for example the JAFZA trace in `data/reference_traces/evidence/jebel_ali_wh_google_earth.png`).
Prefer a KML polygon whenever you can.
