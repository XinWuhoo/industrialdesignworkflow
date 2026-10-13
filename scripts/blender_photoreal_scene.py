"""Set up a photoreal studio scene around the product: Cycles settings, sweep backdrop,
three-point area lighting, and an 85-135 mm camera aimed at the product.

    blender model.blend --python scripts/blender_photoreal_scene.py -- --focal 100 --hdri /path/studio.exr

Re-running replaces the objects it created (all prefixed "STUDIO_"). Works in any unit scale:
sizes come from the bounding box of the mesh objects that are not part of the studio.
"""
import math
import sys

import bpy
from mathutils import Vector

FOCAL_MM = 100
HDRI_PATH = None          # optional studio HDRI for reflections
RESOLUTION = (4000, 3000)
SAMPLES = 1024


def parse_args():
    focal, hdri = FOCAL_MM, HDRI_PATH
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if "--focal" in args:
            focal = float(args[args.index("--focal") + 1])
        if "--hdri" in args:
            hdri = args[args.index("--hdri") + 1]
    return focal, hdri


def clear_studio():
    for obj in [o for o in bpy.data.objects if o.name.startswith("STUDIO_")]:
        bpy.data.objects.remove(obj, do_unlink=True)


def product_bounds():
    pts = [obj.matrix_world @ Vector(c) for obj in bpy.data.objects
           if obj.type == "MESH" and not obj.name.startswith("STUDIO_") for c in obj.bound_box]
    if not pts:
        raise RuntimeError("No mesh objects found to frame.")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def make_sweep(lo, size):
    """Seamless floor that curves up into a back wall behind the product."""
    w, depth, radius, height = size * 8, size * 10, size * 1.5, size * 5
    floor_z, back_y = lo.z, lo.y + size * 2.5
    profile = [(y, floor_z) for y in [back_y - depth + i * (depth / 8) for i in range(9)]]
    for i in range(1, 13):
        a = (i / 12) * (math.pi / 2)
        profile.append((back_y + radius * math.sin(a), floor_z + radius * (1 - math.cos(a))))
    profile.append((back_y + radius, floor_z + height))
    verts = [(x, y, z) for x in (-w / 2, w / 2) for (y, z) in profile]
    n = len(profile)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    mesh = bpy.data.meshes.new("STUDIO_sweep")
    mesh.from_pydata(verts, [], faces)
    for p in mesh.polygons:
        p.use_smooth = True
    obj = link(bpy.data.objects.new("STUDIO_sweep", mesh))
    mat = bpy.data.materials.get("STUDIO_backdrop") or bpy.data.materials.new("STUDIO_backdrop")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.90, 0.89, 0.86, 1)  # near the `surface` token
    bsdf.inputs["Roughness"].default_value = 0.6
    mesh.materials.append(mat)
    return obj


def make_light(name, location, target, size, energy):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = size, size * 0.6
    data.energy = energy
    obj = link(bpy.data.objects.new(name, data))
    obj.location = location
    obj.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    return obj


def main():
    focal, hdri = parse_args()
    scene = bpy.context.scene
    clear_studio()
    lo, hi = product_bounds()
    center = (lo + hi) / 2
    size = max(hi - lo)

    # Render settings
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    try:
        scene.cycles.device = "GPU"
    except TypeError:
        pass
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    try:
        scene.view_settings.view_transform = "AgX"
        for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
            try:
                scene.view_settings.look = look
                break
            except TypeError:
                continue
    except TypeError:
        scene.view_settings.view_transform = "Filmic"

    # World: HDRI for reflections, or a dim neutral grey
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if hdri:
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri, check_existing=True)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.6
    else:
        bg.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
        bg.inputs["Strength"].default_value = 0.15

    make_sweep(lo, size)

    # Camera: three-quarter view, product filling about 65% of the frame width
    cam_data = bpy.data.cameras.new("STUDIO_camera")
    cam_data.lens = focal
    cam_data.sensor_width = 36
    fov = 2 * math.atan(18 / focal)
    dist = (size / 0.65) / (2 * math.tan(fov / 2))
    direction = Vector((math.sin(math.radians(35)), -math.cos(math.radians(35)), 0.35)).normalized()
    cam = link(bpy.data.objects.new("STUDIO_camera", cam_data))
    cam.location = center + direction * dist
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = dist
    cam_data.dof.aperture_fstop = 8

    # Lights: soft key above-left, rim behind, fill opposite the key. Energy scales with distance².
    d = size * 3
    make_light("STUDIO_key", center + Vector((-d, -d * 0.6, d)), center, size * 3, 400 * d * d)
    make_light("STUDIO_rim", center + Vector((d * 0.4, d * 1.2, d * 0.8)), center, size * 2, 250 * d * d)
    make_light("STUDIO_fill", center + Vector((d * 1.2, -d * 0.4, d * 0.3)), center, size * 4, 80 * d * d)

    print(f"STUDIO: product size {size:.4g}, camera {focal:.0f} mm at {dist:.4g}; render F12 when ready")


main()
