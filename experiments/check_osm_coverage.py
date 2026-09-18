"""
Check OSM coverage for the validation candidates and retrieve live OSM ways if available.
"""

import requests
import json
import math
from solarscan.geometry import latlon_to_meters, calculate_shoelace_area, calculate_perimeter

CANDIDATES = [
    {"id": "uos_w5", "lat": 25.2893304, "lon": 55.4783103, "name": "CS Department W5, UoS"},
    {"id": "uos_m13", "lat": 25.28695, "lon": 55.47953, "name": "Engineering M13, UoS"},
    {"id": "uos_m3", "lat": 25.28588, "lon": 55.48512, "name": "Student Center M3, UoS"},
    {"id": "aus_main", "lat": 25.30905, "lon": 55.49122, "name": "AUS Main Building"},
    {"id": "aus_engineering", "lat": 25.31175, "lon": 55.49298, "name": "AUS Engineering Building"},
    {"id": "saf_art", "lat": 25.35824, "lon": 55.38379, "name": "Sharjah Art Foundation"},
    {"id": "kingfisher_lodge", "lat": 25.01258, "lon": 56.36302, "name": "Kingfisher Retreat Kalba"},
    {"id": "saif_wh1", "lat": 25.32845, "lon": 55.51230, "name": "SAIF Zone Cargo Complex"},
    {"id": "saif_wh2", "lat": 25.32410, "lon": 55.51680, "name": "SAIF Zone Depot"},
    {"id": "dubai_mall", "lat": 25.19720, "lon": 55.27970, "name": "Dubai Mall"},
    {"id": "moe_dubai", "lat": 25.11810, "lon": 55.20060, "name": "Mall of the Emirates"},
    {"id": "dha_warehouse", "lat": 25.14320, "lon": 55.23410, "name": "Al Quoz Logistics Warehouse"},
    {"id": "jebel_ali_wh", "lat": 24.97540, "lon": 55.07680, "name": "JAFZA Logistics Depot"},
    {"id": "al_serkal", "lat": 25.14150, "lon": 55.22680, "name": "Alserkal Avenue"},
    {"id": "al_satwa_res", "lat": 25.21540, "lon": 55.26820, "name": "Satwa Residential Block"},
    {"id": "jumeirah_mosque", "lat": 25.23360, "lon": 55.26540, "name": "Jumeirah Mosque"},
    {"id": "nyu_abudhabi", "lat": 24.52380, "lon": 54.43440, "name": "NYU Abu Dhabi"},
    {"id": "masdar_mist", "lat": 24.42850, "lon": 54.61480, "name": "Masdar City Knowledge Center"},
    {"id": "ad_mall", "lat": 24.49520, "lon": 54.38380, "name": "Abu Dhabi Mall"},
    {"id": "mussafah_wh", "lat": 24.36450, "lon": 54.49850, "name": "Mussafah Warehouse"},
    {"id": "sheikh_zayed_mosque", "lat": 24.41280, "lon": 54.47490, "name": "Sheikh Zayed Mosque Annex"},
    {"id": "ajman_city_center", "lat": 25.39950, "lon": 55.47920, "name": "City Centre Ajman"},
    {"id": "ajman_uni", "lat": 25.41250, "lon": 55.51420, "name": "Ajman University J1"},
    {"id": "rak_mall", "lat": 25.77250, "lon": 55.95250, "name": "RAK Mall"},
    {"id": "rak_al_hamra", "lat": 25.68850, "lon": 55.77850, "name": "Al Hamra Village Compound"},
]

headers = {"User-Agent": "SolarScanResearch/0.2.0 (contact@research.org)"}
mirror = "https://overpass-api.de/api/interpreter"

print(f"Querying Overpass for {len(CANDIDATES)} buildings...")
for c in CANDIDATES:
    lat, lon = c["lat"], c["lon"]
    query = f"""[out:json][timeout:10];
    (way["building"](around:200,{lat},{lon});
     relation["building"](around:200,{lat},{lon}););
    out body;>;out skel qt;"""
    try:
        r = requests.post(mirror, data={"data": query}, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            elements = data.get("elements", [])
            ways = [e for e in elements if e.get("type") == "way" and "nodes" in e]
            nodes = {e["id"]: (e["lat"], e["lon"]) for e in elements if e.get("type") == "node"}
            print(f"{c['id']:20} ({c['name']:25}): found {len(ways)} building ways")
            if ways:
                best_way = None
                best_dist = 999999
                best_area = 0
                for w in ways:
                    coords = [nodes[nid] for nid in w["nodes"] if nid in nodes]
                    if len(coords) >= 3:
                        m = latlon_to_meters(coords)
                        a = calculate_shoelace_area(m)
                        cent_lat = sum(p[0] for p in coords) / len(coords)
                        cent_lon = sum(p[1] for p in coords) / len(coords)
                        dy = (cent_lat - lat) * 111000.0
                        dx = (cent_lon - lon) * 111000.0 * math.cos(math.radians(lat))
                        dist = math.hypot(dx, dy)
                        if dist < best_dist:
                            best_dist = dist
                            best_way = w
                            best_area = a
                if best_way:
                    print(f"    -> closest way {best_way['id']}, dist={best_dist:.1f}m, area={best_area:.1f}m2, name={best_way.get('tags', {}).get('name', 'N/A')}")
        else:
            print(f"{c['id']}: status {r.status_code}")
    except Exception as e:
        print(f"{c['id']}: error {e}")
