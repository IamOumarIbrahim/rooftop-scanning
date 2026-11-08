"""Regenerate every result, table, figure and the PDF from the stored data.

    python scripts/reproduce.py            # offline: analysis -> figures -> checks -> tests -> PDF
    python scripts/reproduce.py --online   # first refresh PVGIS, Microsoft footprints, pvlib check, DOIs
    python scripts/reproduce.py --verify   # also fail if any committed result changed (git diff)

No number in the paper is typed by hand: analysis.py writes manuscript/generated/numbers.tex,
and main.tex reads every value from it.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(title, cmd, cwd=ROOT):
    print(f"\n=== {title}\n$ {' '.join(map(str, cmd))}", flush=True)
    if subprocess.run(cmd, cwd=cwd).returncode != 0:
        sys.exit(f"FAILED: {title}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true", help="refresh external data first (needs internet)")
    ap.add_argument("--verify", action="store_true", help="fail if committed outputs change")
    ap.add_argument("--no-pdf", action="store_true", help="skip LaTeX")
    a = ap.parse_args()

    if a.online:
        run("PVGIS yield grids", [PY, "experiments/fetch_pvgis.py"])
        run("Microsoft footprints", [PY, "experiments/fetch_ms_footprints.py"])
        run("pvlib cross-check", [PY, "experiments/crosscheck_pvlib.py"])
        run("Satellite views (Google Maps, needs Chrome + playwright)", [PY, "experiments/fetch_imagery.py"])
        run("Map boundaries (geoBoundaries)", [PY, "experiments/fetch_boundaries.py"])
        run("Reference DOIs", [PY, "scripts/check_references.py"])
    run("Analysis (all numbers and tables)", [PY, "experiments/analysis.py"])
    blender = shutil.which("blender") or next((str(p) for p in sorted(Path("C:/Program Files/Blender Foundation").glob(
        "*/blender.exe"), reverse=True)), None)
    if blender:
        run("3D render (Blender)", [blender, "-b", "--factory-startup", "-P", "experiments/render_w5_blender.py", "--",
                                    "results/scene_w5.json", "manuscript/figures/render_w5.png"])
        run("3D render of the rows (Blender)", [blender, "-b", "--factory-startup", "-P",
                                                "experiments/render_rows_blender.py", "--", "results/results.json",
                                                "manuscript/figures/render_rows.png", "results/render_rows_points.json"])
    else:
        print("Blender not found: keeping the committed render_w5.png and render_rows.png")
    run("Figures", [PY, "experiments/figures.py"])
    run("Manuscript checks", [PY, "scripts/check_manuscript.py"])
    run("Unit tests", [PY, "-m", "pytest", "-q"])
    if not a.no_pdf:
        if shutil.which("latexmk") is None:
            print("latexmk not found: skipping PDF build")
        else:
            run("PDF", ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=ROOT / "manuscript")
    if a.verify:
        run("Outputs unchanged", ["git", "diff", "--exit-code", "--stat", "--",
                                  "results", "manuscript/generated"])
    print("\nAll steps passed.")


if __name__ == "__main__":
    main()
