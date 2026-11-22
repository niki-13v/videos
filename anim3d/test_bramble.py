"""Blender feasibility test: procedural 3D Bramble in a meadow, Cycles CPU render.

    blender -b -P anim3d/test_bramble.py -- out.png
"""
import math
import sys
import time

import bpy

DENOISE = "--denoise" in sys.argv
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/bramble3d.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, rough=0.55, sheen=0.0, spec=0.3, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    if "Sheen Weight" in p.inputs:
        p.inputs["Sheen Weight"].default_value = sheen
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = spec
    if emit:
        p.inputs["Emission Color"].default_value = (*rgb, 1)
        p.inputs["Emission Strength"].default_value = emit
    return m


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


def blob(name, loc, scale, material, rot=(0, 0, 0), parent=None, seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


BROWN, CREAM, PINK = mat("brown", srgb("#a0672f"), 0.7, 0.6), mat("cream", srgb("#f6e0b5"), 0.7, 0.5), mat("pink", srgb("#f4a6b5"), 0.6)
BLACK = mat("black", srgb("#1a1210"), 0.15, spec=0.8)
WHITE = mat("white", (1, 1, 1), 0.3, emit=0.5)
RED = mat("scarf", srgb("#e8413c"), 0.8, 0.8)
CHEEK = mat("cheek", srgb("#ff8fa3"), 0.8)

bpy.ops.object.empty_add(location=(0, 0, 0))
rig = bpy.context.object
rig.name = "Bramble"
blob("body", (0, 0, 0.85), (0.72, 0.62, 0.78), BROWN, parent=rig)
blob("belly", (0, -0.42, 0.8), (0.48, 0.25, 0.55), CREAM, parent=rig)
head = blob("head", (0, 0, 1.95), (0.66, 0.6, 0.6), BROWN, parent=rig)
blob("muzzle", (0, -0.5, 1.8), (0.32, 0.2, 0.24), CREAM, parent=rig)
blob("nose", (0, -0.69, 1.9), (0.11, 0.07, 0.08), BLACK, parent=rig)
blob("mouth", (0, -0.66, 1.7), (0.07, 0.03, 0.05), mat("mouth", srgb("#7a1f2b"), 0.5), parent=rig)
for sx in (-1, 1):
    blob(f"eye{sx}", (sx * 0.24, -0.5, 2.08), (0.1, 0.07, 0.12), BLACK, parent=rig)
    blob(f"glint{sx}", (sx * 0.24 + 0.035, -0.565, 2.13), (0.03, 0.02, 0.03), WHITE, parent=rig)
    blob(f"cheek{sx}", (sx * 0.4, -0.45, 1.82), (0.1, 0.04, 0.07), CHEEK, parent=rig)
    blob(f"ear{sx}", (sx * 0.5, 0.02, 2.45), (0.22, 0.12, 0.22), BROWN, parent=rig)
    blob(f"earin{sx}", (sx * 0.5, -0.07, 2.45), (0.13, 0.06, 0.13), PINK, parent=rig)
    blob(f"arm{sx}", (sx * 0.72, -0.05, 0.95), (0.18, 0.18, 0.42), BROWN, rot=(0, sx * -0.45, 0), parent=rig)
    blob(f"foot{sx}", (sx * 0.32, -0.12, 0.13), (0.24, 0.32, 0.15), BROWN, parent=rig)
    blob(f"pad{sx}", (sx * 0.32, -0.42, 0.13), (0.14, 0.03, 0.09), CREAM, parent=rig)
bpy.ops.mesh.primitive_torus_add(location=(0, 0, 1.38), major_radius=0.5, minor_radius=0.12)
sc = bpy.context.object
sc.scale = (1.0, 0.9, 0.9)
bpy.ops.object.shade_smooth()
sc.data.materials.append(RED)
sc.parent = rig
blob("scarftail", (0.25, -0.5, 1.12), (0.12, 0.05, 0.3), RED, rot=(0.2, 0.3, 0), parent=rig)

# set: rolling hills, trees, flowers
GRASS, GRASS2 = mat("grass", srgb("#7cc950"), 0.9), mat("grass2", srgb("#5fb33d"), 0.9)
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
bpy.context.object.data.materials.append(GRASS)
for x, y, r, m in [(-14, 22, 10, GRASS2), (10, 26, 13, GRASS), (25, 18, 9, GRASS2), (-28, 15, 8, GRASS)]:
    blob("hill", (x, y, -r * 0.55), (r, r, r * 0.8), m)
TRUNK, LEAF = mat("trunk", srgb("#8d5a33"), 0.8), mat("leaf", srgb("#4caf50"), 0.8, 0.3)
APPLE = mat("apple", srgb("#e53935"), 0.3)
for x, y in [(-4.2, 4, ), (4.5, 5)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=2.2, location=(x, y, 1.1))
    bpy.context.object.data.materials.append(TRUNK)
    for dx, dz, r in [(-0.6, 2.6, 0.9), (0.6, 2.6, 0.9), (0, 3.3, 1.05), (0, 2.4, 0.95)]:
        blob("leaf", (x + dx, y, dz), (r, r, r * 0.92), LEAF)
    for dx, dz in [(-0.7, 3.0), (0.5, 3.5), (0.8, 2.4)]:
        blob("apple", (x + dx, y - 0.85, dz), (0.13, 0.13, 0.13), APPLE)
import random

rnd = random.Random(3)
PETALS = [mat(f"p{i}", srgb(c), 0.6) for i, c in enumerate(["#ff6b9d", "#ffd23f", "#ffffff", "#b388ff"])]
for _ in range(40):
    x, y = rnd.uniform(-6, 6), rnd.uniform(-2.5, 6)
    if abs(x) < 1.2 and y < 1:
        continue
    blob("flower", (x, y, 0.06), (0.08, 0.08, 0.05), rnd.choice(PETALS), seg=12)

# world, light, camera
world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
# bright cartoon sky: vertical gradient from light cyan (horizon) to sky blue (top)
coord = world.node_tree.nodes.new("ShaderNodeTexCoord")
sep = world.node_tree.nodes.new("ShaderNodeSeparateXYZ")
ramp = world.node_tree.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (*srgb("#d8f3ff"), 1)
ramp.color_ramp.elements[1].color = (*srgb("#4fb3f5"), 1)
ramp.color_ramp.elements[1].position = 0.55
world.node_tree.links.new(coord.outputs["Generated"], sep.inputs[0])
world.node_tree.links.new(sep.outputs["Z"], ramp.inputs[0])
world.node_tree.links.new(ramp.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(10), math.radians(-30)))
bpy.context.object.data.energy = 2.6
bpy.context.object.data.angle = math.radians(8)
bpy.ops.object.light_add(type="AREA", location=(0, -5, 4))
bpy.context.object.data.energy = 250
bpy.context.object.data.size = 5
bpy.context.object.rotation_euler = (math.radians(50), 0, 0)
bpy.ops.object.camera_add(location=(0, -7.5, 2.1), rotation=(math.radians(86), 0, 0))
cam = bpy.context.object
cam.data.lens = 40
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = DENOISE
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.view_settings.view_transform = "Standard"  # vivid cartoon colours (no filmic wash-out)
scene.view_settings.look = "None"
scene.render.filepath = out
t = time.time()
bpy.ops.render.render(write_still=True)
print(f"RENDER_SECONDS {time.time() - t:.1f}")
