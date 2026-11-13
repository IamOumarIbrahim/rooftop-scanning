"""Scripted walkthrough of SolarScan using Demotive.

Usage:
    python scripts/make_demo.py [WORKDIR]
    python -m demotive.compose takes/solarscan docs/demo.mp4 --gif docs/demo.gif ^
        --logo S --title "SolarScan" ^
        --subtitle "How much solar fits on this roof, and does it pay back?" ^
        --accent "#e07b2a" ^
        --outro-title "SolarScan" ^
        --outro-subtitle "OpenStreetMap + PVGIS · Free data only" ^
        --outro-line "pip install -e ." --outro-line "solarscan gui"
"""

import os
import sys
import tkinter as tk

# Ensure rooftop-scanning and Demotive are importable
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOTIVE_DIR = r"C:\Dev\repos\Public repos\Demotive"
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
if DEMOTIVE_DIR not in sys.path:
    sys.path.insert(0, DEMOTIVE_DIR)

from demotive import Director
from solarscan.gui import App, _dpi_aware


def build_script(app):
    def script(d: Director):
        yield from d.wait(1.0)

        # 1. Enter an address or try the demo building
        yield from d.caption("Enter any location or launch the reference warehouse")
        yield from d.focus(app.building_card, zoom=1.45)
        yield from d.move(app.entry)
        yield from d.click()
        yield from d.type(app.entry, "TCTI warehouse, Dubai")
        yield from d.wait(0.6)
        yield from d.move(app.demo_btn)
        yield from d.click(app.demo_btn.invoke)
        yield from d.wait(0.8)

        # 2. Fast forward through the scan computation
        yield from d.caption("Fetch OSM building outline and lay out module rows")
        yield from d.focus(None)
        yield from d.speed(3)
        yield from d.until(lambda: app.data is not None)
        yield from d.speed(1)
        yield from d.wait(0.8)

        # 3. Realistic module placement with setback & tilt spacing
        yield from d.caption("Realistic module layout with 1.5 m edge setbacks")
        yield from d.focus(app.plan_frame, zoom=1.35)
        yield from d.move(app.plan, dur=1.0)
        yield from d.wait(2.0)

        # 4. KPI tiles & solar generation numbers
        yield from d.caption("549 kWp system yields 938 MWh/yr with PVGIS solar irradiance")
        yield from d.focus(app.tiles_frame, zoom=1.4)
        yield from d.move(app.tiles[0][0].master, dur=0.6)
        yield from d.wait(0.4)
        yield from d.move(app.tiles[1][0].master, dur=0.6)
        yield from d.wait(0.4)
        yield from d.move(app.tiles[3][0].master, dur=0.6)
        yield from d.wait(1.2)

        # 5. Live financial sensitivity adjustments
        yield from d.caption("Adjust cost & electricity tariff — payback updates live")
        yield from d.focus(None)
        yield from d.move(app.cost.scale)
        yield from d.drag_slider(app.cost.scale, 2400, dur=1.0)
        yield from d.wait(0.6)
        yield from d.move(app.price.scale)
        yield from d.drag_slider(app.price.scale, 0.45, dur=1.0)
        yield from d.wait(1.0)

        # 6. Sensitivity matrix
        yield from d.caption("Explore the turnkey cost vs. electricity rate sensitivity matrix")
        yield from d.focus(app.heat_frame, zoom=1.45)
        yield from d.move(app.heat, dur=0.8)
        yield from d.wait(1.8)

        # 7. PDF and web report export
        yield from d.caption("Export one-page executive PDF and interactive web reports")
        yield from d.focus(app.open_pdf.master, zoom=1.4)
        yield from d.move(app.open_pdf, dur=0.6)
        yield from d.wait(0.8)
        yield from d.move(app.open_html, dur=0.6)
        yield from d.wait(1.0)

        yield from d.focus(None)
        yield from d.caption(None)
        yield from d.wait(0.8)

    return script


def main(workdir="takes/solarscan"):
    _dpi_aware()
    root = tk.Tk()
    app = App(root)
    d = Director(root, workdir, size=(1280, 820), pos=(100, 50), fps=30)
    d.run(build_script(app))


if __name__ == "__main__":
    work = sys.argv[1] if len(sys.argv) > 1 else "takes/solarscan"
    main(work)
