"""Close-up of module rows at solar noon on the shortest day in Sharjah (Blender, Cycles): Fig. 1(d).

Run with Blender, not plain Python:
    blender -b --factory-startup -P experiments/render_rows_blender.py -- results/results.json         manuscript/figures/render_rows.png results/render_rows_points.json

Tilt, row spacing and the noon sun height come from results/results.json (written by analysis.py).
The modules are drawn with their low edge on the roof, so the drawn shadow equals the computed one.
Also writes the image positions of a few 3D points, used by figures.py for the labels.
"""
import json
import math
import sys

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
import os
RES, OUT, PTS = (os.path.abspath(a) for a in argv[:3])
R = json.load(open(RES, encoding="utf-8"))
ELEV = R["row_shading"]["noon_elev_deg"]
L, TILT, GCR, H0, W = 2.0, math.radians(R["config"]["default_tilt_deg"]), R["config"]["packing_factor"], 0.0, 1.0
PITCH = L / GCR
DEPTH, RISE = L * math.cos(TILT), L * math.sin(TILT)
NROWS, NCOLS = 3, 4

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, rgb, rough=0.6, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    return m


def obj(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def box(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])


# roof slab
bm = bmesh.new()
box(bm, -1.5, NCOLS * W + 1.5, -2.0, NROWS * PITCH + 1.0, -0.3, 0.0)
obj("Roof", bm, material("roof", (0.80, 0.78, 0.74), rough=0.95))

# modules: low (south) edge at y = r*PITCH, high (north) edge at y = r*PITCH + DEPTH
pv, frame = material("pv", (0.03, 0.07, 0.20), rough=0.15, spec=0.9), material("leg", (0.55, 0.57, 0.6), rough=0.5)
bm, bl = bmesh.new(), bmesh.new()
for r in range(NROWS):
    ys = r * PITCH
    for c in range(NCOLS):
        x0, x1 = c * W + 0.02, (c + 1) * W - 0.02
        a = [bm.verts.new(p) for p in ((x0, ys, H0), (x1, ys, H0), (x1, ys + DEPTH, H0 + RISE), (x0, ys + DEPTH, H0 + RISE))]
        b = [bm.verts.new((p.co.x, p.co.y, p.co.z - 0.035)) for p in a]
        bm.faces.new(a)
        bm.faces.new(list(reversed(b)))
        for i in range(4):
            bm.faces.new([a[i], b[i], b[(i + 1) % 4], a[(i + 1) % 4]])
    for c in range(NCOLS + 1):  # simple legs at the row ends and between modules
        x = min(c * W, NCOLS * W - 0.04)
        if H0 > 0.05:
            box(bl, x, x + 0.04, ys + 0.05, ys + 0.09, 0, H0)
        box(bl, x, x + 0.04, ys + DEPTH - 0.09, ys + DEPTH - 0.05, 0, H0 + RISE - 0.03)
obj("Modules", bm, pv)
obj("Legs", bl, frame)

# sun at solar noon: azimuth 180 (south = -Y), elevation ELEV
e = math.radians(ELEV)
to_sun = Vector((0.0, -math.cos(e), math.sin(e)))
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
sun.data.energy = 6.5
sun.data.angle = math.radians(0.53)
sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.89, 0.96, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

# camera from the east, slightly south and above, so the shadows between rows are visible
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = NROWS * PITCH + 1.6
target = Vector((NCOLS * W * 0.5, NROWS * PITCH * 0.5 - 0.35, 0.2))
cam.location = target + Vector((14.0, -4.2, 6.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "CYCLES"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1800, 1000
scene.render.film_transparent = True
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX"
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)

# label anchors on the east end of row 1 and row 2 (x = right edge)
xe = NCOLS * W - 0.02
ys1 = 1 * PITCH
pts = {
    "row1_low": (xe, ys1, H0), "row1_top": (xe, ys1 + DEPTH, H0 + RISE),
    "row2_low": (xe, ys1 + PITCH, H0),
    "gap_a": (xe, ys1 + DEPTH, 0.0), "gap_b": (xe, ys1 + PITCH, 0.0),
    "shadow_end": (xe, ys1 + DEPTH + RISE / math.tan(e), 0.0),
    "sun_from": (xe, ys1 + DEPTH - 2.2 * math.cos(e), H0 + RISE + 2.2 * math.sin(e)),
}
res = {}
for k, p in pts.items():
    v = world_to_camera_view(scene, cam, Vector(p))
    res[k] = (v.x * scene.render.resolution_x, (1 - v.y) * scene.render.resolution_y)
json.dump({"points": {k: [round(v, 2) for v in p] for k, p in res.items()},
           "size": [scene.render.resolution_x, scene.render.resolution_y]}, open(PTS, "w"), indent=1)
print("rendered", OUT)
