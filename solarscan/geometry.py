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

WGS84_A = 6378137.0                     # semi-major axis (m)
WGS84_E2 = 6.69437999014e-3             # first eccentricity squared


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
    
    Uses a local tangent-plane approximation on the WGS84 ellipsoid:
        y = (lat - lat_0) * (pi / 180) * M(lat_0)
        x = (lon - lon_0) * (pi / 180) * N(lat_0) * cos(lat_0)
    where M and N are the meridional and prime-vertical radii of curvature.
    A single spherical radius (6,371 km) would overstate areas by about 0.2 %
    at UAE latitudes. With M and N, the area agrees with the geodesic area
    (pyproj.Geod) to better than 0.01 % for footprints under 1 km.
    """
    cleaned = sanitize_polygon(coords)
    if not cleaned or len(cleaned) < 3:
        return []

    avg_lat = sum(c[0] for c in cleaned) / len(cleaned)
    avg_lon = sum(c[1] for c in cleaned) / len(cleaned)

    lat_rad = math.radians(avg_lat)
    w = math.sqrt(1.0 - WGS84_E2 * math.sin(lat_rad) ** 2)
    m_radius = WGS84_A * (1.0 - WGS84_E2) / w ** 3
    n_radius = WGS84_A / w
    cos_lat = math.cos(lat_rad)

    meter_coords = []
    for lat, lon in cleaned:
        dlat_rad = math.radians(lat - avg_lat)
        dlon_rad = math.radians(lon - avg_lon)
        y = dlat_rad * m_radius
        x = dlon_rad * n_radius * cos_lat
        meter_coords.append((x, y))
        
    return meter_coords


def calculate_shoelace_area(vertices: List[Tuple[float, float]]) -> float:
    """
    Computes the enclosed area of a 2D planar polygon via the Gauss shoelace formula.
    
    Formula:
        A = 0.5 * | sum_{i=0}^{n-1} (x_i * y_{i+1} - x_{i+1} * y_i) |
    with (x_n, y_n) = (x_0, y_0).
    """
    cleaned = sanitize_polygon(vertices)
    if len(cleaned) < 3:
        return 0.0
    
    n = len(cleaned)
    area = 0.0
    for i in range(n):
        x1, y1 = cleaned[i]
        x2, y2 = cleaned[(i + 1) % n]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def calculate_perimeter(vertices: List[Tuple[float, float]]) -> float:
    """
    Calculates the Euclidean perimeter of a polygon defined by 2D Cartesian vertices.
    """
    cleaned = sanitize_polygon(vertices)
    if len(cleaned) < 3:
        return 0.0
    p = 0.0
    n = len(cleaned)
    for i in range(n):
        x1, y1 = cleaned[i]
        x2, y2 = cleaned[(i + 1) % n]
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
    obstruction_area: float = 0.0,
    holes: Optional[List[List[Tuple[float, float]]]] = None
) -> float:
    """
    Computes usable rooftop area using geometric interior polygon buffering.
    Supports interior cutout courtyards/holes.
    Falls back to analytical perimeter approximation if Shapely is unavailable.
    """
    effective_setback = max(0.0, setback_m)
    effective_obstruction = max(0.0, obstruction_area)
    cleaned_vertices = sanitize_polygon(vertices)
    if SHAPELY_AVAILABLE and len(cleaned_vertices) >= 3:
        try:
            cleaned_holes = []
            if holes:
                for h in holes:
                    ch = sanitize_polygon(h)
                    if len(ch) >= 3:
                        cleaned_holes.append(ch)
            poly = Polygon(cleaned_vertices, holes=cleaned_holes if cleaned_holes else None)
            if not poly.is_valid:
                poly = poly.buffer(0)
            buffered = poly.buffer(-effective_setback)
            if buffered.is_empty:
                return 0.0
            usable = buffered.area - effective_obstruction
            return max(0.0, usable)
        except Exception:
            pass
    
    raw_area = calculate_shoelace_area(cleaned_vertices)
    perimeter = calculate_perimeter(cleaned_vertices)
    return calculate_usable_area(raw_area, perimeter, effective_setback, effective_obstruction)


def usable_polygon(vertices: List[Tuple[float, float]], setback_m: float):
    """The roof polygon shrunk inward by the setback (a shapely geometry; may be empty)."""
    poly = Polygon(sanitize_polygon(vertices))
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly.buffer(-max(0.0, setback_m))


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


def calculate_building_axis(vertices: List[Tuple[float, float]]) -> float:
    """
    Returns the bearing of the building's long axis in degrees, in [0, 180).

    The axis is the long side of the minimum-area bounding rectangle. An axis
    is a line, not a direction, so 30 deg and 210 deg are the same axis. The
    result therefore does not depend on vertex order (clockwise or not).
    Bearings are clockwise from true North (x = East, y = North).
    """
    cleaned = sanitize_polygon(vertices)
    if len(cleaned) < 3:
        return 90.0
    if SHAPELY_AVAILABLE:
        rect = list(Polygon(cleaned).minimum_rotated_rectangle.exterior.coords)[:4]
        edges = [(rect[i], rect[(i + 1) % 4]) for i in range(2)]
    else:
        n = len(cleaned)
        edges = [(cleaned[i], cleaned[(i + 1) % n]) for i in range(n)]
    (x1, y1), (x2, y2) = max(edges, key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
    return round(math.degrees(math.atan2(x2 - x1, y2 - y1)) % 180.0, 2)


def array_azimuth_aligned(axis_deg: float) -> float:
    """
    Facing azimuth of module rows laid parallel to one side of the building.
    A rectangular roof allows rows along either side, so the rows can face any
    of the four directions axis + k*90 deg. We pick the one closest to true
    South (180 deg). The deviation from South is therefore at most 45 deg.
    """
    candidates = [(axis_deg + k * 90.0) % 360.0 for k in range(4)]
    return round(min(candidates, key=lambda a: abs(a - 180.0)), 2)


def calculate_dominant_azimuth(vertices: List[Tuple[float, float]]) -> float:
    """
    Facing azimuth (deg, 0 = N, 90 = E, 180 = S) for building-aligned module rows.
    Kept for backward compatibility. Equals array_azimuth_aligned(calculate_building_axis(v)).
    """
    return array_azimuth_aligned(calculate_building_axis(vertices))
