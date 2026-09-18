import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(7.16, 2.1), dpi=300)
ax.axis('off')
ax.set_xlim(0, 100)
ax.set_ylim(0, 36)

stages = [
    {
        'num': 'STAGE 1',
        'title': 'Query Ingestion',
        'x': 1.0, 'w': 16.6,
        'items': ['Address / Geocode', 'GPS Coordinates', 'Google Maps URL'],
        'badge': 'Centroid (lat, lon)'
    },
    {
        'num': 'STAGE 2',
        'title': 'OSM Retrieval',
        'x': 21.0, 'w': 16.6,
        'items': ['Overpass API QL', 'Search Radius 250 m', 'Building Way Filter'],
        'badge': 'Vector GeoJSON'
    },
    {
        'num': 'STAGE 3',
        'title': 'Geometric Sizing',
        'x': 41.0, 'w': 16.6,
        'items': ['Equirectangular Proj.', 'Shoelace Area (A)', 'Setback Buffer (s)'],
        'badge': 'Net Usable Area'
    },
    {
        'num': 'STAGE 4',
        'title': 'PV Yield Model',
        'x': 61.0, 'w': 16.6,
        'items': ['Dominant Azimuth', 'Orientation Derate', 'Regional Solar PSH'],
        'badge': 'Annual Energy MWh'
    },
    {
        'num': 'STAGE 5',
        'title': 'Feasibility',
        'x': 81.0, 'w': 16.6,
        'items': ['Turnkey CAPEX Model', 'Utility Tariff Savings', 'Simple Payback (Yrs)'],
        'badge': 'Payback & ROI'
    }
]

for st in stages:
    x, w = st['x'], st['w']
    card = FancyBboxPatch((x, 3.0), w, 30.0, boxstyle='Round,pad=0.2,rounding_size=0.8',
                          facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=1.1, zorder=2)
    ax.add_patch(card)
    
    header = FancyBboxPatch((x, 26.0), w, 7.0, boxstyle='Round,pad=0.2,rounding_size=0.8',
                            facecolor='#1e3a8a', edgecolor='#1e3a8a', linewidth=1.0, zorder=3)
    ax.add_patch(header)
    
    ax.text(x + w/2, 30.5, st['num'], ha='center', va='center', fontsize=6.8, fontweight='bold', color='#93c5fd', zorder=4)
    ax.text(x + w/2, 27.8, st['title'], ha='center', va='center', fontsize=7.8, fontweight='bold', color='#ffffff', zorder=4)
    
    y_text = 22.0
    for item in st['items']:
        ax.plot(x + 1.2, y_text, marker='o', markersize=2.5, color='#0284c7', zorder=4)
        ax.text(x + 2.2, y_text, item, ha='left', va='center', fontsize=6.6, color='#1e293b', zorder=4)
        y_text -= 4.0
        
    badge_box = FancyBboxPatch((x + 0.8, 4.2), w - 1.6, 3.8, boxstyle='Round,pad=0.1,rounding_size=0.5',
                               facecolor='#e0f2fe', edgecolor='#7dd3fc', linewidth=0.7, zorder=4)
    ax.add_patch(badge_box)
    ax.text(x + w/2, 6.1, st['badge'], ha='center', va='center', fontsize=6.8, fontweight='bold', color='#0369a1', zorder=5)

for i in range(len(stages) - 1):
    x_start = stages[i]['x'] + stages[i]['w'] + 0.3
    x_end = stages[i+1]['x'] - 0.3
    ax.annotate('', xy=(x_end, 18.0), xytext=(x_start, 18.0),
                arrowprops=dict(facecolor='#0284c7', edgecolor='#0284c7', width=1.4, headwidth=4.5, headlength=5.0))

plt.subplots_adjust(left=0.005, right=0.995, top=0.98, bottom=0.02)
fig.savefig('scratch/test_fig1_clean.png', dpi=300)
print('Saved test_fig1_clean.png')
