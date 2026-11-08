# Contributing

## Add a benchmark building

1. Find the building in OpenStreetMap and note its way ID.
2. Save its footprint: `python -c "from solarscan import capture_fixture; capture_fixture(LAT, LON, 'data/fixtures/<id>.json')"`.
3. Add a row to `data/buildings.csv` (no area numbers: they are computed).
4. Trace the roof by hand, following [`data/reference_traces/README.md`](data/reference_traces/README.md).
5. Run `python scripts/reproduce.py`.

## Code rules

- Every number in the paper must come from `experiments/analysis.py`. Never type a result into `main.tex`.
- Every new function needs a test in `tests/`. Prefer tests that check a physical property or a
  closed-form answer over tests that repeat the code.
- Fail loudly. Never return made-up data when a lookup fails.
- No paid APIs or licensed GIS software as required dependencies.

## Before a pull request

```bash
python scripts/reproduce.py --verify
```
