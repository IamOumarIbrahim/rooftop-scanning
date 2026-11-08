"""Render the case-study roof and its module rows in Blender (Cycles).

Run with Blender, not plain Python:
    blender -b --factory-startup -P experiments/render_w5_blender.py -- results/scene_w5.json manuscript/figures/render_w5.png

Geometry comes from results/scene_w5.json (written by experiments/analysis.py):
the OSM footprint, the usable roof after the setback, and every module footprint.
OSM has no height for this building, so the building height is illustrative.
"""
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
import os
SCENE_JSON, OUT_PNG = os.path.abspath(argv[0]), os.path.abspath(argv[1])
HEIGHT = 14.0          # illustrative building height (m)
PARAPET = 1.0          # parapet height (m)
RACK = 0.35            # height of the lowest module edge above the roof (m)

with open(SCENE_JSON, encoding="utf-8") as f:
    S = json.load(f)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
cx = sum(p[0] for p in S["footprint"]) / len(S["footprint"])
cy = sum(p[1] for p in S["footprint"]) / len(S["footprint"])
shift = lambda p: (p[0] - cx, p[1] - cy)  # noqa: E731


def material(name, rgb, rough=0.6, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    return m


def mesh_object(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def prism(bm, ring, z0, z1):
    """Closed vertical prism from a polygon ring."""
    bot = [bm.verts.new((*shift(p), z0)) for p in ring]
    top = [bm.verts.new((*shift(p), z1)) for p in ring]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(ring)
    for i in range(n):
        bm.faces.new([bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]])


# Ground
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=140)
ground = mesh_object("Ground", bm, material("ground", (0.78, 0.70, 0.58), rough=0.95))
ground.is_shadow_catcher = True  # keep only the shadow; background stays transparent

# Building body and roof
bm = bmesh.new()
prism(bm, S["footprint"], 0, HEIGHT)
mesh_object("Building", bm, material("concrete", (0.86, 0.82, 0.74), rough=0.8))

# Parapet: thin walls along every footprint edge
bm = bmesh.new()
fp = S["footprint"]
for i in range(len(fp)):
    (x0, y0), (x1, y1) = shift(fp[i]), shift(fp[(i + 1) % len(fp)])
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-6:
        continue
    nx, ny = -(y1 - y0) / L * 0.15, (x1 - x0) / L * 0.15
    ring = [(x0 - nx + cx, y0 - ny + cy), (x1 - nx + cx, y1 - ny + cy), (x1 + nx + cx, y1 + ny + cy), (x0 + nx + cx, y0 + ny + cy)]
    prism(bm, ring, HEIGHT, HEIGHT + PARAPET)
mesh_object("Parapet", bm, material("parapet", (0.90, 0.87, 0.80), rough=0.8))

# Setback strip: the roof outside the usable polygon is shown in a warm tone
bm = bmesh.new()
verts = [bm.verts.new((*shift(p), HEIGHT + 0.02)) for p in S["usable"]]
bm.faces.new(verts)
mesh_object("Usable", bm, material("usable", (0.70, 0.70, 0.70), rough=0.9))
bm = bmesh.new()
verts = [bm.verts.new((*shift(p), HEIGHT + 0.01)) for p in S["footprint"]]
bm.faces.new(verts)
mesh_object("Strip", bm, material("strip", (0.93, 0.62, 0.36), rough=0.9))

# Modules: tilted towards south (low edge at the south side of each footprint)
tilt = math.radians(S["tilt_deg"])
rise = S["length_m"] * math.sin(tilt)
bm = bmesh.new()
for m in S["modules"]:
    xs, ys = [p[0] for p in m], [p[1] for p in m]
    x0, x1 = min(xs) - cx + 0.02, max(xs) - cx - 0.02
    y0, y1 = min(ys) - cy, max(ys) - cy
    zs, zn = HEIGHT + RACK, HEIGHT + RACK + rise
    v = [bm.verts.new(c) for c in ((x0, y0, zs), (x1, y0, zs), (x1, y1, zn), (x0, y1, zn),
                                   (x0, y0, zs - 0.04), (x1, y0, zs - 0.04), (x1, y1, zn - 0.04), (x0, y1, zn - 0.04))]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[i] for i in f])
mesh_object("Modules", bm, material("pv", (0.03, 0.07, 0.20), rough=0.18, spec=0.9))

# Light and sky
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
sun.data.energy = 4.0
sun.data.angle = math.radians(2.0)
sun.rotation_euler = (math.radians(40), 0, math.radians(200))
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.80, 0.86, 0.95, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9

# Camera: from the south-east, looking down at the roof
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 42
target = Vector((0, 0, HEIGHT * 0.75))
cam.location = Vector((48, -64, 66))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

# Render settings
scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.device = "CPU"
scene.render.resolution_x, scene.render.resolution_y = 1800, 1350
scene.render.film_transparent = True
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX" if "AgX" in [v.name for v in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
scene.render.filepath = OUT_PNG
bpy.ops.render.render(write_still=True)
print("rendered", OUT_PNG, S["n_modules"], "modules")
