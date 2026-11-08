"""Capture georeferenced satellite views of selected buildings from Google Maps.

Each view is centered on the OSM footprint, with labels and the 3D globe switched off,
so the image is a flat Web-Mercator picture with a known scale:
    meters per CSS pixel = 156543.03392 * cos(latitude) / 2**zoom   (zoom: whole numbers only)
The page interface is hidden; only the map canvas is captured. Google's attribution
text is saved with each image and must be printed with any figure that uses it.

The images are Google content. They are cached in data/_cache/imagery/ (not committed);
only the attributed paper figures are published.

Usage:  python experiments/fetch_imagery.py      (needs internet, Chrome and: pip install playwright)
"""
import datetime
import json
import math
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
from analysis import TRACES  # noqa: E402

OUT = os.path.join(ROOT, "data", "_cache", "imagery")
VIEW_W, VIEW_H, DPR = 1200, 900, 2
MAX_ZOOM = 20.0  # about the native resolution of the imagery; more zoom only blurs
BUILDINGS = ["uos_w5", "jebel_ali_wh", "dubai_ondemand_auto", "ajman_public_market", "ajman_empost_hub", "uos_m13",
             "dubai_tcti_warehouse", "ad_mussafah_wh1", "ajman_salem_center"]
HIDE_UI = "body * { visibility: hidden !important; } canvas { visibility: visible !important; }"


def view_for(bid):
    with open(os.path.join(ROOT, "data", "fixtures", bid + ".json"), encoding="utf-8") as f:
        osm = json.load(f)["polygon_coords"]
    pts = [(c[0], c[1]) for c in osm] + [(lat, lon) for lon, lat in TRACES.get(bid, [])]
    lats, lons = [p[0] for p in pts], [p[1] for p in pts]
    lat0 = sum(c[0] for c in osm) / len(osm)
    lon0 = sum(c[1] for c in osm) / len(osm)
    span = max((max(lats) - min(lats)) * 111_000, (max(lons) - min(lons)) * 111_000 * math.cos(math.radians(lat0)))
    mpp_needed = max(span, 25) * 1.8 / VIEW_H  # building fills ~55 % of the image height
    zoom = min(MAX_ZOOM, max(15.0, math.log2(156543.03392 * math.cos(math.radians(lat0)) / mpp_needed)))
    # Whole zoom levels only: Google Maps draws a fractional zoom at a different scale than the
    # URL states, which made overlays up to 1.9x too large. floor() keeps the whole roof in view.
    return lat0, lon0, float(math.floor(zoom))


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True,
                                    args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H}, locale="en-US",
                                device_scale_factor=DPR)
        for bid in (sys.argv[1:] or BUILDINGS):
            lat, lon, zoom = view_for(bid)
            page.goto(f"https://www.google.com/maps/@{lat:.7f},{lon:.7f},{zoom}z/data=!3m1!1e3?hl=en")
            page.wait_for_timeout(20000)
            for name in ("Labels", "Globe view"):
                box = page.locator("[role=checkbox]", has_text=name).first
                if box.count() and box.get_attribute("aria-checked") == "true":
                    box.evaluate("e => e.click()")
                    page.wait_for_timeout(2500)
            page.wait_for_timeout(8000)
            attribution = page.evaluate(
                "() => [...document.querySelectorAll('span,div')].map(e => e.innerText || '')"
                ".find(t => t.startsWith('Imagery') && t.length < 120) || ''")
            page.add_style_tag(content=HIDE_UI)
            page.wait_for_timeout(1500)
            png = os.path.join(OUT, f"{bid}.png")
            page.screenshot(path=png)
            meta = {"id": bid, "center_lat": lat, "center_lon": lon, "zoom": zoom,
                    "m_per_px": 156543.03392 * math.cos(math.radians(lat)) / 2 ** zoom / DPR,
                    "width_px": VIEW_W * DPR, "height_px": VIEW_H * DPR,
                    "attribution": attribution.strip() or "Imagery (c) Google",
                    "captured": datetime.date.today().isoformat(), "source": "Google Maps satellite view"}
            with open(os.path.join(OUT, f"{bid}.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=1)
            print(bid, zoom, f'{meta["m_per_px"]:.3f} m/px', meta["attribution"])
        browser.close()


if __name__ == "__main__":
    main()
