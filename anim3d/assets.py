"""Build every character/object in 3D (Blender) and render transparent sprites.

    blender -b -P anim3d/assets.py -- --out assets3d --group animals [--res 512] [--samples 32] [--denoise]
    groups: bramble, animals, fruits, shapes, things, bg, all

Each object is rendered in 3 face states: idle, blink, talk. The 2D engine (anim/) bounces,
squashes and moves the sprites, so one set of renders serves every future video.
"""
import math
import os
import random
import sys

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = arg("--out", "assets3d")
GROUP = arg("--group", "all")
RES = int(arg("--res", "512"))
SAMPLES = int(arg("--samples", "32"))
DENOISE = "--denoise" in ARGS
ONLY = arg("--only")  # comma list of sprite names, for quick tests
ONLY_COLORS = arg("--colors")  # comma list of colour names, to split big groups across machines
os.makedirs(OUT, exist_ok=True)

COLORS = {"red": "#e53935", "blue": "#1e88e5", "yellow": "#fdd835", "green": "#43a047",
          "orange": "#fb8c00", "purple": "#8e24aa", "pink": "#ec407a", "brown": "#8d6e63"}
FACE_STATES = ["idle", "blink", "talk"]


# ------------------------------------------------------------------ helpers
def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


_MATS = {}


def mat(hexcol, rough=0.55, sheen=0.3, spec=0.35, emit=0.0, key=None):
    key = key or f"{hexcol}-{rough}-{sheen}-{spec}-{emit}"
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*srgb(hexcol), 1)
    p.inputs["Roughness"].default_value = rough
    if "Sheen Weight" in p.inputs:
        p.inputs["Sheen Weight"].default_value = sheen
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = spec
    if emit:
        p.inputs["Emission Color"].default_value = (*srgb(hexcol), 1)
        p.inputs["Emission Strength"].default_value = emit
    _MATS[key] = m
    return m


def clear_scene():
    for o in list(bpy.data.objects):
        if not o.name.startswith("RIG_"):
            bpy.data.objects.remove(o, do_unlink=True)


def blob(loc, scale, m, rot=(0, 0, 0), seg=40):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(8, seg // 2), location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def cyl(loc, r, depth, m, rot=(0, 0, 0), verts=40):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def rounded_box(loc, size, m, bevel=0.2):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    mod = o.modifiers.new("bevel", "BEVEL")
    mod.width = bevel
    mod.segments = 6
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def tube(points, radius, m, closed=False):
    """A rounded line through 3D points (smiles, stems, strings)."""
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, (x, y, z) in zip(sp.points, points):
        p.co = (x, y, z, 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new("tube", cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(m)
    return o


def chaikin(pts, n=2):
    """Round off sharp corners (corner-cutting), so shapes look like soft toys."""
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % len(pts)]
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * z0 + 0.25 * z1), (0.25 * x0 + 0.75 * x1, 0.25 * z0 + 0.75 * z1)]
        pts = out
    return pts


def puffy(outline, depth, m, loc=(0, 0, 0), bevel=0.18):
    """Extrude a 2D outline (list of (x, z)) into a soft, toy-like 3D shape facing the camera."""
    cu = bpy.data.curves.new("puffy", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = depth
    cu.bevel_depth = bevel
    cu.bevel_resolution = 8
    sp = cu.splines.new("POLY")
    sp.points.add(len(outline) - 1)
    for p, (x, z) in zip(sp.points, outline):
        p.co = (x, z, 0, 1)
    sp.use_cyclic_u = True
    o = bpy.data.objects.new("puffy", cu)
    bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = loc
    o.data.materials.append(m)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.shade_smooth()
    if hasattr(o.data, "set_sharp_from_angle"):
        o.data.set_sharp_from_angle(angle=math.radians(50))
    return o


def arc_pts(cx, cz, y, r, a0, a1, n=16):
    return [(cx + r * math.cos(a), y, cz + r * math.sin(a)) for a in [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]]


BLACK = lambda: mat("#1a1210", 0.12, 0, 0.9, key="eye")
WHITE = lambda: mat("#ffffff", 0.3, 0, 0.3, 0.6, key="glint")
CHEEK = lambda: mat("#ff8fa3", 0.85, 0, 0.1, key="cheek")
MOUTH = lambda: mat("#7a1f2b", 0.5, 0, 0.3, key="mouth")
TONGUE = lambda: mat("#f47c8a", 0.5, 0, 0.3, key="tongue")


def face(cx, cz, y, s, state, gap=0.33, eye_h=0.13, cheeks=True, mouth_dz=-0.28):
    """Eyes + cheeks + mouth on a surface facing -Y at depth y. state: idle | blink | talk | happy."""
    for sx in (-1, 1):
        ex, ez = cx + sx * gap * s, cz + 0.06 * s
        if state in ("blink",):
            tube(arc_pts(ex, ez + 0.05 * s, y - 0.02, 0.1 * s, math.radians(200), math.radians(340)), 0.025 * s, BLACK())
        elif state == "happy":
            tube(arc_pts(ex, ez - 0.06 * s, y - 0.02, 0.1 * s, math.radians(20), math.radians(160)), 0.025 * s, BLACK())
        else:
            blob((ex, y + 0.02 * s, ez), (0.1 * s, 0.07 * s, eye_h * s), BLACK())
            blob((ex + 0.035 * s, y - 0.045 * s, ez + 0.05 * s), (0.032 * s, 0.02 * s, 0.032 * s), WHITE())
        if cheeks:
            blob((cx + sx * (gap + 0.17) * s, y + 0.03 * s, cz - 0.14 * s), (0.1 * s, 0.03 * s, 0.065 * s), CHEEK())
    mz = cz + mouth_dz * s
    if state == "talk":
        blob((cx, y + 0.01 * s, mz), (0.12 * s, 0.05 * s, 0.11 * s), MOUTH())
        blob((cx, y - 0.01 * s, mz - 0.05 * s), (0.07 * s, 0.04 * s, 0.04 * s), TONGUE())
    else:
        tube(arc_pts(cx, mz + 0.1 * s, y - 0.01, 0.12 * s, math.radians(215), math.radians(325)), 0.022 * s, BLACK())


# ------------------------------------------------------------------ scene setup
def setup(kind="sprite"):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = DENOISE
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = kind == "sprite"
    scene.render.image_settings.color_mode = "RGBA" if kind == "sprite" else "RGB"
    if not scene.world:
        scene.world = bpy.data.worlds.new("w")
    w = scene.world
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("#cfe9ff"), 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    for name, loc, energy, size in [("RIG_key", (-3, -5, 6), 700, 4), ("RIG_fill", (4, -4, 2), 250, 5), ("RIG_rim", (0, 5, 5), 500, 4)]:
        if name not in bpy.data.objects:
            ld = bpy.data.lights.new(name, "AREA")
            ld.energy, ld.size = energy, size
            lo = bpy.data.objects.new(name, ld)
            scene.collection.objects.link(lo)
            lo.location = loc
            direction = [-v for v in loc]
            lo.rotation_euler = _look(direction)
    if "RIG_cam" not in bpy.data.objects:
        cd = bpy.data.cameras.new("RIG_cam")
        cd.type = "ORTHO"
        co = bpy.data.objects.new("RIG_cam", cd)
        scene.collection.objects.link(co)
        scene.camera = co
    return scene


def _look(d):
    x, y, z = d
    return (math.atan2(math.hypot(x, y), -z) if False else math.pi / 2 - math.atan2(z, math.hypot(x, y)), 0, math.atan2(x, -y) * -1)


def camera(center_z, ortho, res_x=None, res_y=None):
    res_x, res_y = res_x or RES, res_y or RES
    scene = bpy.context.scene
    cam = bpy.data.objects["RIG_cam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.location = (0, -12, center_z + 12 * math.tan(math.radians(6)))
    cam.rotation_euler = (math.radians(84), 0, 0)
    scene.render.resolution_x, scene.render.resolution_y = res_x, res_y


def shadow_catcher():
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    p = bpy.context.object
    p.is_shadow_catcher = True


def render(name):
    path = os.path.join(OUT, name + ".png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("SPRITE", name, flush=True)


def want(name):
    return not ONLY or name in ONLY.split(",")


# ------------------------------------------------------------------ objects (radius ~1, centre z=1.2, bottom at ~0.2)
C = 1.2


def build_thing(kind, col, state):
    m = mat(col, 0.45, 0.2, 0.45)
    if kind == "balloon":
        blob((0, 0, C + 0.1), (0.82, 0.8, 1.0), mat(col, 0.18, 0, 0.8))
        blob((0, 0.02, C - 0.97), (0.1, 0.1, 0.08), mat(col, 0.18, 0, 0.8))
        tube([(0, 0, C - 1.0), (0.08, 0, C - 1.3), (-0.06, 0, C - 1.6), (0.05, 0, C - 1.9)], 0.012, mat("#5d4037", 0.7, key="string"))
        face(0, C + 0.1, -0.78, 0.95, state)
    elif kind == "ball":
        blob((0, 0, C), (0.95, 0.95, 0.95), m)
        bpy.ops.mesh.primitive_torus_add(location=(0, 0, C), major_radius=0.9, minor_radius=0.14, rotation=(0, math.pi / 2, 0))
        bpy.context.object.scale = (1.05, 1.05, 1.05)
        bpy.ops.object.shade_smooth()
        bpy.context.object.data.materials.append(mat("#ffffff", 0.45, key="white_band"))
        face(-0.35, C + 0.05, -0.9, 0.55, state)
    elif kind == "star":
        pts = []
        for k in range(10):
            r = 1.0 if k % 2 == 0 else 0.48
            a = math.pi / 2 + k * math.pi / 5
            pts.append((r * math.cos(a), r * math.sin(a)))
        puffy(chaikin(pts, 1), 0.18, m, loc=(0, 0.18, C), bevel=0.16)
        face(0, C - 0.05, -0.42, 0.62, state)
    elif kind == "heart":
        pts = []
        for k in range(120):
            a = 2 * math.pi * k / 120
            x = 16 * math.sin(a) ** 3
            z = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
            pts.append((x / 17, z / 17 + 0.1))
        puffy(chaikin(pts, 3), 0.2, m, loc=(0, 0.2, C), bevel=0.16)
        face(0, C + 0.1, -0.42, 0.7, state)
    elif kind == "car":
        rounded_box((0, 0, C - 0.25), (2.2, 1.1, 0.7), m, 0.25)
        rounded_box((0, 0, C + 0.3), (1.25, 1.0, 0.65), m, 0.25)
        for x in (-0.3, 0.3):
            rounded_box((x, -0.47, C + 0.32), (0.48, 0.1, 0.42), mat("#bbdefb", 0.1, 0, 0.9, key="glass"), 0.08)
        for x in (-0.68, 0.68):
            cyl((x, -0.45, C - 0.6), 0.32, 0.25, mat("#2b2b2e", 0.6, key="tyre"), rot=(math.pi / 2, 0, 0))
            cyl((x, -0.58, C - 0.6), 0.14, 0.05, mat("#cfd8dc", 0.3, key="hub"), rot=(math.pi / 2, 0, 0))
        face(0, C - 0.2, -0.56, 0.5, state, gap=0.4)
    elif kind == "cupcake":
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.62, radius2=0.85, depth=0.9, location=(0, 0, C - 0.45))
        bpy.context.object.data.materials.append(mat("#ffcc80", 0.6, key="wrapper"))
        for dx, dz, r in [(-0.45, 0.15, 0.45), (0.45, 0.15, 0.45), (0, 0.4, 0.6), (0, 0.1, 0.62)]:
            blob((dx, 0, C + dz), (r, r * 0.9, r * 0.85), mat(col, 0.35, 0.4, 0.5))
        blob((0, -0.05, C + 1.0), (0.17, 0.17, 0.17), mat("#e53935", 0.2, 0, 0.8, key="cherrytop"))
        face(0, C + 0.25, -0.62, 0.6, state)
    elif kind == "flower":
        for k in range(6):
            a = k * math.pi / 3
            blob((0.58 * math.cos(a), 0.1, C + 0.58 * math.sin(a)), (0.42, 0.15, 0.42), m)
        blob((0, -0.02, C), (0.52, 0.25, 0.52), mat("#ffd54f", 0.5, key="flowermid"))
        face(0, C, -0.27, 0.48, state)
    elif kind == "fish":
        blob((-0.1, 0, C), (0.9, 0.55, 0.65), m)
        puffy([(0, 0), (0.6, 0.45), (0.6, -0.45)], 0.08, m, loc=(0.65, 0.04, C), bevel=0.06)
        face(-0.4, C + 0.05, -0.5, 0.55, state, gap=0.3)
    elif kind == "apple":
        blob((-0.25, 0, C), (0.7, 0.75, 0.85), m)
        blob((0.25, 0, C), (0.7, 0.75, 0.85), m)
        tube([(0, 0, C + 0.75), (0.05, 0, C + 1.0), (0.15, 0, C + 1.12)], 0.04, mat("#5d4037", 0.7, key="stem"))
        blob((0.35, -0.05, C + 1.0), (0.25, 0.08, 0.12), mat("#4caf50", 0.5, key="leaf"), rot=(0, -0.4, 0))
        face(0, C + 0.05, -0.74, 0.8, state)


def build_shape(kind, col, state):
    m = mat(col, 0.45, 0.2, 0.45)
    if kind == "circle":
        pts = [(math.cos(2 * math.pi * k / 64), math.sin(2 * math.pi * k / 64)) for k in range(64)]
    elif kind == "oval":
        pts = [(1.2 * math.cos(2 * math.pi * k / 64), 0.78 * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    elif kind == "square":
        pts = [(-0.88, -0.88), (0.88, -0.88), (0.88, 0.88), (-0.88, 0.88)]
    elif kind == "rectangle":
        pts = [(-1.2, -0.68), (1.2, -0.68), (1.2, 0.68), (-1.2, 0.68)]
    elif kind == "triangle":
        pts = [(0, 1.0), (1.0, -0.8), (-1.0, -0.8)]
    elif kind == "diamond":
        pts = [(0, 1.1), (0.78, 0), (0, -1.1), (-0.78, 0)]
    elif kind in ("heart", "star"):
        return build_thing(kind, col, state)
    if kind in ("square", "rectangle", "triangle", "diamond"):
        pts = chaikin([p for i, p in enumerate(pts) for p in [p, (0.5 * (p[0] + pts[(i + 1) % len(pts)][0]), 0.5 * (p[1] + pts[(i + 1) % len(pts)][1]))]], 3)
    puffy(pts, 0.25, m, loc=(0, 0.2, C), bevel=0.22)
    fz = {"triangle": -0.2}.get(kind, 0.0)
    face(0, C + fz, -0.42, 0.72 if kind != "triangle" else 0.6, state)


def build_fruit(kind, state):
    if kind == "apple":
        return build_thing("apple", "#e53935", state)
    if kind == "banana":
        pts = []
        for k in range(17):
            a = math.radians(200 + k * 140 / 16)
            pts.append((1.05 * math.cos(a), C + 0.55 + 0.95 * math.sin(a)))
        for i, (x, z) in enumerate(pts):
            r = 0.13 + 0.17 * math.sin(math.pi * i / 16)
            blob((x, 0, z), (r * 1.4, r * 1.2, r * 1.2), mat("#ffe135", 0.5, key="banana"), seg=24)
        blob((pts[0][0] - 0.05, 0, pts[0][1] + 0.02), (0.07, 0.07, 0.07), mat("#6d4c2f", 0.7, key="bananatip"))
        face(0, C - 0.3, -0.32, 0.55, state, gap=0.3)
    elif kind == "orange":
        blob((0, 0, C), (0.95, 0.95, 0.92), mat("#fb8c00", 0.65, 0.2, 0.3, key="orange"))
        blob((0.25, -0.05, C + 0.92), (0.28, 0.1, 0.12), mat("#4caf50", 0.5, key="leaf"), rot=(0, -0.3, 0))
        face(0, C + 0.05, -0.93, 0.78, state)
    elif kind == "strawberry":
        o = blob((0, 0, C - 0.05), (0.85, 0.75, 0.95), mat("#e53935", 0.35, 0.2, 0.5, key="strawberry"))
        o.data.vertices.foreach_get  # noqa: keep simple
        rnd = random.Random(1)
        for _ in range(26):
            a, h = rnd.uniform(-1.2, 1.2), rnd.uniform(-0.75, 0.6)
            r = 0.85 * math.sqrt(max(0.05, 1 - (h / 0.95) ** 2))
            blob((r * math.sin(a), -r * math.cos(a) * 0.88, C - 0.05 + h), (0.035, 0.03, 0.05), mat("#ffe082", 0.4, key="seed"), seg=10)
        for k in range(6):
            a = k * math.pi / 3
            blob((0.35 * math.cos(a), 0.35 * math.sin(a) * 0.5, C + 0.85), (0.3, 0.12, 0.08), mat("#43a047", 0.5, key="sleaf"), rot=(0, 0, a))
        face(0, C + 0.1, -0.72, 0.62, state)
    elif kind == "grapes":
        pts = [(0, 0.55), (-0.38, 0.55), (0.38, 0.55), (-0.2, 0.2), (0.2, 0.2), (-0.55, 0.2), (0.55, 0.2), (0, -0.15),
               (-0.38, -0.15), (0.38, -0.15), (-0.2, -0.48), (0.2, -0.48), (0, -0.78)]
        for x, z in pts:
            blob((x, 0, C + z), (0.27, 0.27, 0.27), mat("#8e24aa", 0.25, 0.3, 0.6, key="grape"), seg=24)
        blob((0.1, -0.05, C + 0.9), (0.32, 0.08, 0.14), mat("#4caf50", 0.5, key="leaf"))
        face(0, C + 0.05, -0.3, 0.55, state)
    elif kind == "watermelon":
        def half(r, n=40):
            return [(r * math.cos(math.pi + math.pi * k / n), r * math.sin(math.pi + math.pi * k / n)) for k in range(n + 1)]
        puffy(half(1.2), 0.3, mat("#43a047", 0.5, key="rind"), loc=(0, 0.12, C + 0.45), bevel=0.1)
        puffy(half(1.08), 0.32, mat("#f1f8e9", 0.6, key="melonwhite"), loc=(0, 0.06, C + 0.45), bevel=0.1)
        puffy(half(0.98), 0.34, mat("#ef5350", 0.4, 0.1, 0.5, key="melon"), loc=(0, 0.0, C + 0.45), bevel=0.1)
        for x, z in [(-0.6, -0.1), (0.6, -0.1), (-0.32, -0.5), (0.32, -0.5), (0, -0.75)]:
            blob((x, -0.46, C + 0.45 + z), (0.05, 0.03, 0.08), BLACK(), seg=12)
        face(0, C + 0.2, -0.47, 0.5, state)
    elif kind == "pear":
        m = mat("#c0ca33", 0.5, 0.2, 0.4, key="pear")
        blob((0, 0, C - 0.3), (0.78, 0.72, 0.68), m)
        blob((0, 0, C + 0.35), (0.48, 0.45, 0.55), m)
        tube([(0, 0, C + 0.85), (0.05, 0, C + 1.05), (0.12, 0, C + 1.12)], 0.04, mat("#5d4037", 0.7, key="stem"))
        face(0, C - 0.25, -0.7, 0.58, state)
    elif kind == "cherry":
        for x in (-0.48, 0.5):
            blob((x, 0, C - 0.3), (0.5, 0.48, 0.5), mat("#c62828", 0.2, 0.1, 0.7, key="cherry"))
            face(x, C - 0.28, -0.47, 0.36, state, gap=0.3)
        tube([(-0.45, 0, C + 0.15), (-0.3, 0, C + 0.6), (0, 0, C + 0.95), (0.1, 0, C + 1.05)], 0.035, mat("#5d8a2f", 0.6, key="cstem"))
        tube([(0.5, 0, C + 0.18), (0.4, 0, C + 0.6), (0.2, 0, C + 0.95), (0.1, 0, C + 1.05)], 0.035, mat("#5d8a2f", 0.6, key="cstem"))


def build_animal(kind, state):
    if kind == "cow":
        for sx in (-1, 1):
            bpy.ops.mesh.primitive_cone_add(radius1=0.1, depth=0.4, location=(sx * 0.45, 0.05, C + 0.95), rotation=(0, sx * -0.4, 0))
            bpy.ops.object.shade_smooth()
            bpy.context.object.data.materials.append(mat("#fff3e0", 0.5, key="horn"))
            blob((sx * 0.98, 0.05, C + 0.4), (0.35, 0.14, 0.18), mat("#ffffff", 0.7, 0.4, key="cowwhite"), rot=(0, sx * 0.3, 0))
        blob((0, 0, C), (0.85, 0.75, 0.9), mat("#ffffff", 0.7, 0.4, key="cowwhite"))
        blob((-0.4, -0.45, C + 0.45), (0.25, 0.25, 0.2), mat("#2b2220", 0.6, key="spot"))
        blob((0.55, -0.3, C + 0.05), (0.18, 0.3, 0.25), mat("#2b2220", 0.6, key="spot"))
        blob((0, -0.55, C - 0.45), (0.6, 0.35, 0.36), mat("#f8a5b6", 0.6, 0.3, key="snout"))
        for sx in (-1, 1):
            blob((sx * 0.22, -0.88, C - 0.42), (0.07, 0.03, 0.1), mat("#8a3a48", 0.5, key="nostril"))
        face(0, C + 0.15, -0.72, 0.8, state, cheeks=False, mouth_dz=-0.95)
    elif kind == "pig":
        for sx in (-1, 1):
            puffy([(0, 0), (0.35, 0.05), (0.2, 0.45)], 0.05, mat("#f48fb1", 0.6, key="pigear"), loc=(sx * 0.45 - (0.2 if sx < 0 else 0), 0.05, C + 0.7), bevel=0.05)
        blob((0, 0, C), (0.95, 0.82, 0.85), mat("#f9b4c4", 0.6, 0.4, key="pig"))
        blob((0, -0.75, C - 0.1), (0.36, 0.18, 0.26), mat("#f48fb1", 0.55, 0.3, key="pigsnout"))
        for sx in (-1, 1):
            blob((sx * 0.12, -0.92, C - 0.1), (0.06, 0.03, 0.1), mat("#8a3a48", 0.5, key="nostril"))
        face(0, C + 0.2, -0.72, 0.8, state, mouth_dz=-0.65)
    elif kind in ("duck", "chick"):
        col = "#ffeb3b" if kind == "duck" else "#fff176"
        blob((0, 0, C), (0.85, 0.8, 0.85), mat(col, 0.65, 0.6, key=kind))
        if kind == "duck":
            blob((0, -0.82, C - 0.15 + (0.05 if state != "talk" else 0.1)), (0.42, 0.2, 0.12), mat("#ff9800", 0.4, key="beak"))
            blob((0, -0.78, C - 0.32 - (0.0 if state != "talk" else 0.12)), (0.36, 0.18, 0.1), mat("#fb8c00", 0.4, key="beak2"))
            face(0, C + 0.25, -0.72, 0.75, "blink" if state == "blink" else "idle", mouth_dz=5)
        else:
            for k in (-1, 0, 1):
                blob((k * 0.12, 0, C + 0.88), (0.08, 0.08, 0.16), mat(col, 0.6, key=kind))
            bpy.ops.mesh.primitive_cone_add(radius1=0.15, depth=0.3 + (0.1 if state == "talk" else 0), location=(0, -0.85, C - 0.15), rotation=(math.pi / 2, 0, 0))
            bpy.context.object.data.materials.append(mat("#ff9800", 0.4, key="beak"))
            face(0, C + 0.2, -0.75, 0.75, "blink" if state == "blink" else "idle", mouth_dz=5)
    elif kind == "cat":
        for sx in (-1, 1):
            puffy([(0, 0), (0.5, 0.0), (0.3, 0.55)], 0.1, mat("#ffb74d", 0.6, 0.4, key="cat"), loc=(sx * 0.55 - (0.25 if sx < 0 else -0.0), 0.1, C + 0.55), bevel=0.06)
        blob((0, 0, C), (0.95, 0.8, 0.82), mat("#ffb74d", 0.6, 0.5, key="cat"))
        blob((0, -0.62, C - 0.3), (0.38, 0.22, 0.26), mat("#fff3e0", 0.6, 0.4, key="catmuzzle"))
        blob((0, -0.83, C - 0.15), (0.09, 0.05, 0.06), mat("#f06292", 0.4, key="catnose"))
        for sx in (-1, 1):
            for dz in (-0.15, -0.28):
                tube([(sx * 0.3, -0.8, C + dz), (sx * 0.95, -0.6, C + dz + (dz + 0.2) * 0.6)], 0.012, BLACK())
        face(0, C + 0.18, -0.7, 0.78, state, mouth_dz=-0.62)
    elif kind == "dog":
        for sx in (-1, 1):
            blob((sx * 0.82, 0.05, C + 0.05), (0.25, 0.18, 0.55), mat("#8d5a33", 0.7, 0.5, key="dogear"), rot=(0, sx * 0.25, 0))
        blob((0, 0, C), (0.85, 0.78, 0.85), mat("#d7a46f", 0.7, 0.5, key="dog"))
        blob((0, -0.6, C - 0.35), (0.45, 0.28, 0.32), mat("#f5deb3", 0.7, 0.4, key="dogmuzzle"))
        blob((0, -0.85, C - 0.18), (0.15, 0.08, 0.1), BLACK())
        blob((0.4, -0.65, C + 0.25), (0.22, 0.08, 0.2), mat("#8d5a33", 0.7, 0.5, key="dogear"))
        face(0, C + 0.18, -0.72, 0.75, state, mouth_dz=-0.72)
    elif kind == "sheep":
        rnd = random.Random(4)
        for k in range(22):
            a = k * 2 * math.pi / 22
            blob((0.8 * math.cos(a), 0.15, C + 0.75 * math.sin(a)), (0.32, 0.3, 0.32), mat("#ffffff", 0.9, 0.8, key="wool"), seg=20)
        blob((0, 0.1, C), (0.85, 0.5, 0.8), mat("#ffffff", 0.9, 0.8, key="wool"))
        blob((0, -0.35, C - 0.05), (0.5, 0.25, 0.58), mat("#6d4c41", 0.7, 0.3, key="sheepface"))
        for sx in (-1, 1):
            blob((sx * 0.62, -0.25, C + 0.15), (0.25, 0.1, 0.12), mat("#5d4037", 0.7, key="sheepear"))
        face(0, C + 0.05, -0.58, 0.55, state, cheeks=False, mouth_dz=-0.6)
    elif kind == "frog":
        m = mat("#43a047", 0.4, 0.2, 0.5, key="frog")
        blob((0, 0, C - 0.1), (1.0, 0.75, 0.72), m)
        for sx in (-1, 1):
            blob((sx * 0.5, -0.1, C + 0.5), (0.3, 0.3, 0.3), m)
            blob((sx * 0.5, -0.35, C + 0.52), (0.18, 0.08, 0.2), mat("#ffffff", 0.3, key="frogeye"))
            if state != "blink":
                blob((sx * 0.5, -0.42, C + 0.5), (0.1, 0.05, 0.12), BLACK())
            else:
                tube(arc_pts(sx * 0.5, C + 0.55, -0.44, 0.1, math.radians(200), math.radians(340)), 0.025, BLACK())
        if state == "talk":
            blob((0, -0.72, C - 0.2), (0.32, 0.05, 0.14), MOUTH())
        else:
            tube(arc_pts(0, C + 0.15, -0.74, 0.45, math.radians(220), math.radians(320)), 0.03, BLACK())
        for sx in (-1, 1):
            blob((sx * 0.62, -0.55, C - 0.12), (0.12, 0.03, 0.08), CHEEK())
    elif kind == "lion":
        for k in range(16):
            a = k * 2 * math.pi / 16
            blob((0.88 * math.cos(a), 0.2, C + 0.88 * math.sin(a)), (0.33, 0.25, 0.33), mat("#e67e22", 0.8, 0.6, key="mane"), seg=20)
        for sx in (-1, 1):
            blob((sx * 0.55, 0, C + 0.6), (0.18, 0.1, 0.18), mat("#fbc02d", 0.6, 0.4, key="lion"))
        blob((0, 0, C), (0.78, 0.6, 0.76), mat("#fbc02d", 0.6, 0.5, key="lion"))
        blob((0, -0.45, C - 0.3), (0.36, 0.22, 0.26), mat("#fff3c4", 0.6, 0.4, key="lionmuzzle"))
        blob((0, -0.66, C - 0.12), (0.12, 0.06, 0.08), mat("#6d4c41", 0.5, key="lionnose"))
        face(0, C + 0.15, -0.55, 0.72, state, mouth_dz=-0.65)


# ------------------------------------------------------------------ Bramble rig (body, head states, arms)
def build_bramble(part, state="idle"):
    B, CR, PK = mat("#a0672f", 0.7, 0.6, key="bear"), mat("#f6e0b5", 0.7, 0.5, key="bearcream"), mat("#f4a6b5", 0.6, key="bearpink")
    RED = mat("#e8413c", 0.8, 0.8, key="scarf")
    if part == "body":
        blob((0, 0, 0.85), (0.72, 0.62, 0.78), B)
        blob((0, -0.42, 0.8), (0.48, 0.25, 0.55), CR)
        for sx in (-1, 1):
            blob((sx * 0.32, -0.12, 0.13), (0.24, 0.32, 0.15), B)
            blob((sx * 0.32, -0.42, 0.13), (0.14, 0.03, 0.09), CR)
        bpy.ops.mesh.primitive_torus_add(location=(0, 0, 1.45), major_radius=0.48, minor_radius=0.13)
        bpy.context.object.scale = (1.0, 0.9, 0.85)
        bpy.ops.object.shade_smooth()
        bpy.context.object.data.materials.append(RED)
        blob((0.25, -0.52, 1.2), (0.13, 0.05, 0.3), RED, rot=(0.2, 0.3, 0))
    elif part == "head":
        blob((0, 0, 2.05), (0.66, 0.6, 0.6), B)
        blob((0, -0.5, 1.9), (0.32, 0.2, 0.24), CR)
        blob((0, -0.69, 2.0), (0.11, 0.07, 0.08), BLACK())
        for sx in (-1, 1):
            blob((sx * 0.5, 0.02, 2.55), (0.22, 0.12, 0.22), B)
            blob((sx * 0.5, -0.07, 2.55), (0.13, 0.06, 0.13), PK)
        face(0, 2.12, -0.52, 0.75, state, gap=0.32, mouth_dz=-0.45)
    elif part in ("armL", "armR"):
        sx = -1 if part == "armL" else 1
        blob((sx * 0.72, -0.05, 1.0), (0.18, 0.18, 0.42), B, rot=(0, sx * -0.45, 0))


# ------------------------------------------------------------------ backgrounds
def build_bg(kind):
    clear_scene()
    scene = setup("bg")
    G1, G2 = mat("#7cc950", 0.9, key="grass"), mat("#5fb33d", 0.9, key="grass2")
    w = scene.world
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type not in ("BACKGROUND", "OUTPUT_WORLD"):
            nt.nodes.remove(n)
    coord, sep, ramp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*srgb("#d8f3ff"), 1)
    ramp.color_ramp.elements[1].color = (*srgb("#4fb3f5"), 1)
    ramp.color_ramp.elements[1].position = 0.55
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], nt.nodes["Background"].inputs[0])
    nt.nodes["Background"].inputs[1].default_value = 1.0
    cam = bpy.data.objects["RIG_cam"]
    cam.data.type = "PERSP"
    cam.data.lens = 35
    vertical = kind.endswith("_v")
    base = kind.replace("_v", "")
    scene.render.resolution_x, scene.render.resolution_y = (1080, 1920) if vertical else (1920, 1080)
    cam.location = (0, -9, 2.2)
    cam.rotation_euler = (math.radians(84), 0, 0)
    rnd = random.Random(2)
    if base == "meadow":
        bpy.ops.mesh.primitive_plane_add(size=120)
        bpy.context.object.data.materials.append(G1)
        for x, y, r, m in [(-14, 22, 10, G2), (10, 26, 13, G1), (25, 18, 9, G2), (-28, 15, 8, G1), (0, 40, 16, G2)]:
            blob((x, y, -r * 0.55), (r, r, r * 0.8), m)
        for x, y, s in [(-5.6, 4, 1.0), (5.8, 5, 1.1), (-9, 10, 1.2), (10, 12, 1.3)]:
            cyl((x, y, 1.1 * s), 0.22 * s, 2.2 * s, mat("#8d5a33", 0.8, key="trunk"))
            for dx, dz, r in [(-0.6, 2.6, 0.9), (0.6, 2.6, 0.9), (0, 3.3, 1.05), (0, 2.4, 0.95)]:
                blob((x + dx * s, y, dz * s), (r * s, r * s, r * s * 0.92), mat("#4caf50", 0.8, 0.3, key="leafy"))
            for dx, dz in [(-0.7, 3.0), (0.5, 3.5), (0.8, 2.4)]:
                blob((x + dx * s, y - 0.85 * s, dz * s), (0.13 * s,) * 3, mat("#e53935", 0.3, key="treeapple"))
        for x, y in [(-2.8, 2.5), (3.2, 3.0), (-7, 6)]:
            for dx, r in [(-0.45, 0.45), (0, 0.6), (0.45, 0.45)]:
                blob((x + dx, y, r * 0.5), (r, r * 0.9, r * 0.8), mat("#66bb6a", 0.8, 0.3, key="bush"))
        petals = ["#ff6b9d", "#ffd23f", "#ffffff", "#b388ff"]
        for _ in range(70):
            x, y = rnd.uniform(-9, 9), rnd.uniform(-3, 8)
            blob((x, y, 0.07), (0.09, 0.09, 0.05), mat(rnd.choice(petals), 0.6), seg=12)
    elif base == "beach":
        bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0))
        bpy.context.object.data.materials.append(mat("#ffe0a3", 0.9, key="sand"))
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 108, 0.03))
        bpy.context.object.data.materials.append(mat("#29b6f6", 0.08, 0, 0.9, key="sea"))
        for x, y in [(-6, 6), (7, 9)]:
            for k in range(9):
                blob((x + math.sin(k * 0.25) * 0.3, y, k * 0.45 + 0.2), (0.28, 0.28, 0.3), mat("#a1887f", 0.8, key="palm"), seg=20)
            top = (x + math.sin(2) * 0.3, y, 4.1)
            for a in range(7):
                ang = a * 2 * math.pi / 7
                blob((top[0] + 1.1 * math.cos(ang), y + 0.4 * math.sin(ang), top[2] - 0.3), (1.3, 0.35, 0.12),
                     mat("#43a047", 0.6, 0.3, key="frond"), rot=(0, 0.35, ang))
        for _ in range(14):
            blob((rnd.uniform(-8, 8), rnd.uniform(-2, 6), 0.05), (0.18, 0.12, 0.06), mat(rnd.choice(["#ff8a80", "#ffffff", "#ffd180"]), 0.4), seg=12)
        blob((3.5, 4, 0.3), (0.6, 0.6, 0.35), mat("#ff7043", 0.5, key="bucket"))
    elif base == "playroom":
        bpy.ops.mesh.primitive_plane_add(size=60)
        bpy.context.object.data.materials.append(mat("#d7a86e", 0.6, key="floor"))
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 8, 10), rotation=(math.pi / 2, 0, 0))
        bpy.context.object.data.materials.append(mat("#fff3e0", 0.9, key="wall"))
        blob((0, 1, 0.02), (5, 2.2, 0.02), mat("#ce93d8", 0.9, key="rug"))
        for k, c in enumerate(["#e53935", "#1e88e5", "#fdd835", "#43a047", "#8e24aa"]):
            rounded_box((-6 + k * 0.75, 4, 0.35), (0.65, 0.65, 0.65), mat(c, 0.4), 0.08)
        rounded_box((6, 5, 1.0), (2.2, 0.6, 2.0), mat("#a1887f", 0.6, key="shelf"), 0.06)
        blob((5.5, 4.4, 2.3), (0.35, 0.35, 0.35), mat("#1e88e5", 0.3))
        blob((6.5, 4.4, 2.3), (0.35, 0.35, 0.35), mat("#ffeb3b", 0.3))
        rounded_box((-6, 7.9, 4.5), (3, 0.1, 2.4), mat("#81d4fa", 0.1, 0, 0.6, 0.6, key="window"), 0.05)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(10), math.radians(-30)))
    bpy.context.object.data.energy = 2.6
    bpy.context.object.data.angle = math.radians(8)
    scene.camera = cam
    render(f"bg_{kind}")


# ------------------------------------------------------------------ main
def sprite(name, builder, ortho=3.2, center=C):
    if not want(name):
        return
    clear_scene()
    setup("sprite")
    camera(center, ortho)
    builder()
    render(name)


def main():
    groups = ["bramble", "animals", "fruits", "shapes", "things", "bg"] if GROUP == "all" else GROUP.split(",")
    if "bramble" in groups:
        global RES
        RES = RES * 2  # Bramble is shown big, so render him sharper
        for part in ("body", "armL", "armR"):
            sprite(f"bramble_{part}", lambda p=part: build_bramble(p), ortho=3.6, center=1.45)
        for state in ("idle", "blink", "talk", "happy"):
            sprite(f"bramble_head_{state}", lambda s=state: build_bramble("head", s), ortho=3.6, center=1.45)
        RES = RES // 2
    if "animals" in groups:
        for kind in ["cow", "pig", "duck", "chick", "cat", "dog", "sheep", "frog", "lion"]:
            for st in FACE_STATES:
                sprite(f"animal_{kind}_{st}", lambda k=kind, s=st: build_animal(k, s))
    if "fruits" in groups:
        for kind in ["apple", "banana", "orange", "strawberry", "grapes", "watermelon", "pear", "cherry"]:
            for st in FACE_STATES:
                sprite(f"fruit_{kind}_{st}", lambda k=kind, s=st: build_fruit(k, s))
    if "shapes" in groups:
        for kind in ["circle", "square", "triangle", "rectangle", "oval", "diamond", "heart", "star"]:
            for cname, col in COLORS.items():
                if ONLY_COLORS and cname not in ONLY_COLORS.split(","):
                    continue
                for st in FACE_STATES:
                    sprite(f"shape_{kind}_{cname}_{st}", lambda k=kind, c=col, s=st: build_shape(k, c, s), ortho=3.4)
    if "things" in groups:
        for kind in ["balloon", "ball", "car", "cupcake", "flower", "fish", "apple"]:
            for cname, col in COLORS.items():
                if ONLY_COLORS and cname not in ONLY_COLORS.split(","):
                    continue
                for st in FACE_STATES:
                    sprite(f"thing_{kind}_{cname}_{st}", lambda k=kind, c=col, s=st: build_thing(k, c, s),
                           ortho=3.8 if kind in ("balloon", "car") else 3.2, center=C - 0.3 if kind == "balloon" else C)
    if "bg" in groups:
        for kind in ["meadow", "beach", "playroom", "meadow_v", "beach_v", "playroom_v"]:
            if want(f"bg_{kind}"):
                build_bg(kind)


main()
