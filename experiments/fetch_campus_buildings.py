"""
Fetch real OSM buildings around University of Sharjah and save cleanly as JSON.
"""

import requests
import json
import os
from solarscan.geometry import latlon_to_meters, calculate_shoelace_area, calculate_perimeter

headers = {'User-Agent': 'SolarScanAcademic/0.2.0 (research@sharjah.ac.ae)'}
q = """[out:json][timeout:25];
(
  way["building"](around:800,25.2893,55.4783);
);
out body;
>;
out skel qt;"""

m = 'https://overpass-api.de/api/interpreter'
r = requests.post(m, data={'data': q}, headers=headers, timeout=20)
if r.status_code == 200:
    data = r.json()
    elements = data.get('elements', [])
    ways = [e for e in elements if e.get('type') == 'way' and 'nodes' in e]
    nodes = {e['id']: (e['lat'], e['lon']) for e in elements if e.get('type') == 'node'}
    
    valid_buildings = []
    for w in ways:
        coords = [nodes[nid] for nid in w['nodes'] if nid in nodes]
        if len(coords) >= 4:
            meters = latlon_to_meters(coords)
            area = calculate_shoelace_area(meters)
            perimeter = calculate_perimeter(meters)
            tags = w.get('tags', {})
            # strip non-ascii or safely handle name
            raw_name = tags.get('name:en', tags.get('name', tags.get('ref', f"Building_{w['id']}")))
            ascii_name = raw_name.encode('ascii', 'ignore').decode('ascii').strip()
            if not ascii_name:
                ascii_name = f"Building_{w['id']}"
            
            if 300.0 <= area <= 20000.0:
                valid_buildings.append({
                    "id": w['id'],
                    "name": ascii_name,
                    "ref": tags.get('ref', ''),
                    "area_m2": round(area, 2),
                    "perimeter_m": round(perimeter, 2),
                    "nodes_count": len(coords),
                    "polygon_coords": coords
                })
    
    out_file = os.path.join("data", "campus_buildings_raw.json")
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(valid_buildings, fp, indent=2)
    print(f"Successfully saved {len(valid_buildings)} valid campus buildings to {out_file}!")
else:
    print(f"Failed with status: {r.status_code}")
