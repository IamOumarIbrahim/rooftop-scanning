"""
Geometry module for rooftop solar pre-feasibility analysis.
Provides local metric projection, shoelace area calculation, perimeter calculation,
setback derating, and dominant azimuth orientation estimation.
"""

import math
from typing import List, Tuple, Optional

try:
    from shapely.geometry import Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def sanitize_polygon(coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Sanitizes polygon vertices:
    - Removes trailing identical closing vertex if present (coords[-1] == coords[0])
    - Removes consecutive duplicate vertices within 1e-7 tolerance
    - Validates that coordinates are finite numbers
    """
    if not coords:
        return []

    cleaned = []
    for pt in coords:
        if not (math.isfinite(pt[0]) and math.isfinite(pt[1])):
            raise ValueError(f"Non-finite coordinate encountered: {pt}")
        if not cleaned:
            cleaned.append(pt)
        else:
            prev = cleaned[-1]
            if math.hypot(pt[0] - prev[0], pt[1] - prev[1]) > 1e-7:
                cleaned.append(pt)

    if len(cleaned) > 1 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < 1e-7:
        cleaned.pop()

    return cleaned


def latlon_to_meters(coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Projects geographic coordinates (latitude, longitude in degrees) into a
    local Cartesian metric frame (x, y in meters) centered at the polygon centroid.
    
    Uses an equirectangular approximation centered at the mean latitude:
        y = (lat - lat_0) * (pi / 180) * R_earth
        x = (lon - lon_0) * (pi / 180) * R_earth * cos(lat_0)
    where R_earth = 6,371,000 meters.
    
    For building-scale footprints (< 500 m span), distortion is below 0.01%.
    """
    cleaned = sanitize_polygon(coords)
    if not cleaned or len(cleaned) < 3:
        return []
    
    avg_lat = sum(c[0] for c in cleaned) / len(cleaned)
    avg_lon = sum(c[1] for c in cleaned) / len(cleaned)
    
    r_earth = 6371000.0  # Earth radius in meters (WGS84 volumetric mean)
    lat_rad = math.radians(avg_lat)
    cos_lat = math.cos(lat_rad)
    
    meter_coords = []
    for lat, lon in cleaned:
        dlat_rad = math.radians(lat - avg_lat)
        dlon_rad = math.radians(lon - avg_lon)
        y = dlat_rad * r_earth
        x = dlon_rad * r_earth * cos_lat
        meter_coords.append((x, y))
        
    return meter_coords


def calculate_shoelace_area(vertices: List[Tuple[float, float]]) -> float:
    """
    Computes the enclosed area of a 2D planar polygon via the Gauss shoelace formula.
    
    Formula:
        A = 0.5 * | sum_{i=0}^{n-1} (x_i * y_{i+1} - x_{i+1} * y_i) |
    with (x_n, y_n) = (x_0, y_0).
    """
    if len(vertices) < 3:
        return 0.0
    
    n = len(vertices)
    area = 0.0
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def calculate_perimeter(vertices: List[Tuple[float, float]]) -> float:
    """
    Calculates the Euclidean perimeter of a polygon defined by 2D Cartesian vertices.
    """
    if len(vertices) < 3:
        return 0.0
    p = 0.0
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        p += math.hypot(x2 - x1, y2 - y1)
    return p


def calculate_usable_area(
    raw_area: float,
    perimeter: float,
    setback_m: float,
    obstruction_area: float = 0.0
) -> float:
    """
    Derives usable rooftop area by subtracting perimeter setback buffer and
    known rooftop obstruction zones.
    
    Analytical perimeter approximation:
        A_usable = max(0.0, raw_area - (perimeter * setback_m) - obstruction_area)
    """
    effective_setback = max(0.0, setback_m)
    effective_obstruction = max(0.0, obstruction_area)
    usable = raw_area - (perimeter * effective_setback) - effective_obstruction
    return max(0.0, usable)


def calculate_usable_area_buffered(
    vertices: List[Tuple[float, float]],
    setback_m: float,
    obstruction_area: float = 0.0
) -> float:
    """
    Computes usable rooftop area using geometric interior polygon buffering.
    Falls back to analytical perimeter approximation if Shapely is unavailable.
    """
    effective_setback = max(0.0, setback_m)
    effective_obstruction = max(0.0, obstruction_area)
    if SHAPELY_AVAILABLE and len(vertices) >= 3:
        try:
            poly = Polygon(vertices)
            if not poly.is_valid:
                poly = poly.buffer(0)
            buffered = poly.buffer(-effective_setback)
            if buffered.is_empty:
                return 0.0
            usable = buffered.area - effective_obstruction
            return max(0.0, usable)
        except Exception:
            pass
    
    raw_area = calculate_shoelace_area(vertices)
    perimeter = calculate_perimeter(vertices)
    return calculate_usable_area(raw_area, perimeter, effective_setback, effective_obstruction)


def calculate_polygon_centroid(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculates the true geometric planar centroid (Cx, Cy) using the second-moment
    Gauss shoelace formula.
    """
    cleaned = sanitize_polygon(vertices)
    if not cleaned:
        return (0.0, 0.0)
    if len(cleaned) < 3:
        return (sum(p[0] for p in cleaned) / len(cleaned), sum(p[1] for p in cleaned) / len(cleaned))

    n = len(cleaned)
    area_factor = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = cleaned[i]
        x1, y1 = cleaned[(i + 1) % n]
        cross = (x0 * y1 - x1 * y0)
        area_factor += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    area = area_factor / 2.0
    if abs(area) < 1e-9:
        return (sum(p[0] for p in cleaned) / len(cleaned), sum(p[1] for p in cleaned) / len(cleaned))

    cx = cx / (6.0 * area)
    cy = cy / (6.0 * area)
    return (cx, cy)


def calculate_bounding_box(vertices: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """
    Calculates axis-aligned bounding box (min_x, min_y, max_x, max_y).
    """
    if not vertices:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [p[0] for p in vertices]
    ys = [p[1] for p in vertices]
    return (min(xs), min(ys), max(xs), max(ys))


def calculate_aspect_ratio(vertices: List[Tuple[float, float]]) -> float:
    """
    Calculates bounding box aspect ratio (major dimension / minor dimension >= 1.0).
    """
    min_x, min_y, max_x, max_y = calculate_bounding_box(vertices)
    dx = abs(max_x - min_x)
    dy = abs(max_y - min_y)
    if min(dx, dy) < 1e-6:
        return 1.0
    return round(max(dx, dy) / min(dx, dy), 3)


def calculate_dominant_azimuth(vertices: List[Tuple[float, float]]) -> float:
    """
    Derives roof azimuth orientation in degrees [0, 360) based on the longest
    edge of the polygon footprint.
    
    Convention:
        0 deg = North
        90 deg = East
        180 deg = South
        270 deg = West
    """
    cleaned = sanitize_polygon(vertices)
    if len(cleaned) < 2:
        return 180.0
    
    max_len = -1.0
    dominant_angle = 180.0
    n = len(cleaned)
    
    for i in range(n):
        x1, y1 = cleaned[i]
        x2, y2 = cleaned[(i + 1) % n]
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist > max_len and dist > 1e-6:
            max_len = dist
            dx = x2 - x1
            dy = y2 - y1
            # Angle relative to North (Y axis) clockwise
            angle = math.degrees(math.atan2(dx, dy)) % 360.0
            dominant_angle = angle
            
    return round(dominant_angle, 2)
