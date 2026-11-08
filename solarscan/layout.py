"""
Module-by-module layout of tilted rows on a flat roof.

Rows run east-west and modules face south. Each module is a rectangle of
width W (east-west) and slant length L, tilted by beta, so its footprint depth
is L*cos(beta). Rows repeat every pitch = L / GCR, where GCR (ground cover ratio)
is the share of roof covered by module area; GCR = 0.70 matches the NREL
flat-roof assumption used for the packing factor.

A module is placed only if its whole footprint lies inside the usable polygon.
We try a small grid of row and column offsets and keep the one that fits most
modules. This gives a realistic module count to compare with the simple
packing-factor estimate A_u * k / (W * L).
"""
import math
from typing import Dict, List, Tuple

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.prepared import prep


def layout_modules(
    usable: Polygon,
    width_m: float = 1.0,
    length_m: float = 2.0,
    tilt_deg: float = 15.0,
    gcr: float = 0.70,
    azimuth_deg: float = 180.0,
    steps: int = 0,
) -> Dict:
    """
    Returns the best layout. 'modules' is a list of module footprints, each a list of
    4 (x, y) corners in the same frame as 'usable' (x = east, y = north, meters).
    azimuth_deg is the direction the modules face (180 = south).
    """
    depth = length_m * math.cos(math.radians(tilt_deg))
    pitch = length_m / gcr
    if usable.is_empty or usable.area <= 0:
        return {"modules": [], "n": 0, "pitch_m": pitch, "depth_m": depth}
    if not steps:  # finer offset search on small roofs, coarser on very large ones
        steps = 6 if usable.area < 10_000 else (3 if usable.area < 60_000 else 2)
    # Rotate the roof so that the facing direction points to -y (south), lay out, rotate back.
    rot = azimuth_deg - 180.0
    origin = usable.centroid
    work = affinity.rotate(usable, rot, origin=origin) if rot else usable
    minx, miny, maxx, maxy = work.bounds
    target = prep(work)
    best: List[Tuple[float, float, float, float]] = []
    for i in range(steps):
        for j in range(steps):
            ox, oy = width_m * i / steps, pitch * j / steps
            placed = []
            y = miny + oy
            while y + depth <= maxy + 1e-9:
                x = minx + ox
                while x + width_m <= maxx + 1e-9:
                    if target.contains(box(x, y, x + width_m, y + depth)):
                        placed.append((x, y, x + width_m, y + depth))
                    x += width_m
                y += pitch
            if len(placed) > len(best):
                best = placed
    modules = []
    for x0, y0, x1, y1 in best:
        rect = box(x0, y0, x1, y1)
        if rot:
            rect = affinity.rotate(rect, -rot, origin=origin)
        modules.append([tuple(c) for c in list(rect.exterior.coords)[:4]])
    return {"modules": modules, "n": len(modules), "pitch_m": pitch, "depth_m": depth,
            "width_m": width_m, "length_m": length_m, "tilt_deg": tilt_deg, "gcr": gcr, "azimuth_deg": azimuth_deg}


def packing_estimate(usable_area: float, gcr: float = 0.70, width_m: float = 1.0, length_m: float = 2.0) -> float:
    """Number of modules implied by the simple packing-factor rule."""
    return usable_area * gcr / (width_m * length_m)
