"""Pictures of the tool for the paper: the desktop interface and the PDF report, both for the demo
building (TCTI warehouse, Dubai; B17 in the benchmark).

Writes manuscript/figures/fig_gui.png and fig_report.png. Needs a display (the window is opened and
captured) and Poppler's pdftoppm for the report page.

Usage:  python experiments/screenshots.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "manuscript", "figures")
sys.path.insert(0, ROOT)


def gui():
    path = os.path.join(OUT, "fig_gui.png")
    subprocess.run([sys.executable, "-m", "solarscan.cli", "gui", "--screenshot", path], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL, timeout=180)
    print("wrote", path)


def report():
    from solarscan.cli import demo_kwargs, run_scan
    tmp = tempfile.mkdtemp()
    try:
        pdf = run_scan(**demo_kwargs(), out_dir=tmp, fmt="pdf")
        subprocess.run(["pdftoppm", "-r", "300", "-png", "-singlefile", pdf, os.path.join(tmp, "page")], check=True)
        img = Image.open(os.path.join(tmp, "page.png")).convert("RGB")
        # crop the white margins, keeping a thin border
        bg = Image.new("RGB", img.size, (255, 255, 255))
        from PIL import ImageChops
        box = ImageChops.difference(img, bg).getbbox()
        pad = 40
        img = img.crop((max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, img.width),
                        min(box[3] + pad, img.height)))
        img.save(os.path.join(OUT, "fig_report.png"), optimize=True)
        print("wrote", os.path.join(OUT, "fig_report.png"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    gui()
    report()
