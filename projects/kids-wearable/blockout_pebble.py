"""Concept A · Pebble — parametric blockout for Blender (1 unit = 1 cm).

    blender --background --python projects/kids-wearable/blockout_pebble.py

Builds the pod, the display lens with a simple clock face, the side button, and a strap
closed as if on a child's wrist (46 x 36 mm wrist section), with adjustment holes, pin and keeper.
Object names follow projects/kids-wearable/cmf.json so blender_apply_cmf.py can assign materials.
"""
import math

import bpy

# --- parameters (cm) ---
POD_L, POD_W = 3.8, 3.4        # along strap, across strap
POD_TOP, POD_BOTTOM = 0.85, 0.35  # height above / below the pod's mid plane
POD_PLAN_EXP = 0.7             # plan shape: 1 = ellipse, smaller = squarer
POD_PROFILE_EXP = 0.6          # side profile: smaller = flatter top, steeper sides
LENS_R = 1.15
STRAP_W, STRAP_T = 2.0, 0.3
WRIST_RX, WRIST_RZ = 2.4, 1.85  # band centreline, slightly larger than the wrist
BAND_EXP = 0.62                # band loop shape: smaller = flatter top under the pod


def sgnpow(w, e):
    return math.copysign(abs(w) ** e, w)


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def mesh_object(name, verts, faces, smooth=True, subsurf=1):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = smooth
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if subsurf:
        mod = obj.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = mod.render_levels = subsurf
    return obj


def band_point(t):
    """Point and outward normal on the band centreline (superellipse in the XZ plane)."""
    x = WRIST_RX * sgnpow(math.cos(t), BAND_EXP)
    z = WRIST_RZ * sgnpow(math.sin(t), BAND_EXP)
    return x, z


def band_frame(t, dt=1e-3):
    x0, z0 = band_point(t - dt)
    x1, z1 = band_point(t + dt)
    tx, tz = x1 - x0, z1 - z0
    n = math.hypot(tx, tz)
    tx, tz = tx / n, tz / n
    nx, nz = tz, -tx  # outward for a counter-clockwise loop
    return band_point(t), (nx, nz)


def rounded_rect(w, h, r, seg=4):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def sweep(name, t0, t1, steps, w, h, offset=0.0, closed=False, subsurf=1):
    """Sweep a rounded-rect section (w across the strap, h radial) along the band."""
    sec = rounded_rect(w, h, min(w, h) * 0.45)
    verts, faces = [], []
    n_steps = steps if closed else steps + 1
    for i in range(n_steps):
        t = t0 + (t1 - t0) * i / steps
        (x, z), (nx, nz) = band_frame(t)
        for sy, sr in sec:
            r = sr + offset
            verts.append((x + nx * r, sy, z + nz * r))
    m = len(sec)
    rings = n_steps if closed else n_steps - 1
    for i in range(rings):
        a, b = i * m, ((i + 1) % n_steps) * m
        for j in range(m):
            faces.append((a + j, a + (j + 1) % m, b + (j + 1) % m, b + j))
    if not closed:
        faces.append(tuple(range(m))[::-1])
        last = (n_steps - 1) * m
        faces.append(tuple(range(last, last + m)))
    return mesh_object(name, verts, faces, subsurf=subsurf)


def pod(z0):
    nu, nv = 64, 32
    verts, faces = [], []
    for j in range(1, nv):
        v = -math.pi / 2 + math.pi * j / nv
        cz = POD_TOP if v > 0 else POD_BOTTOM
        for i in range(nu):
            u = 2 * math.pi * i / nu
            r = sgnpow(math.cos(v), POD_PROFILE_EXP)
            verts.append((POD_L / 2 * r * sgnpow(math.cos(u), POD_PLAN_EXP),
                          POD_W / 2 * r * sgnpow(math.sin(u), POD_PLAN_EXP),
                          z0 + cz * sgnpow(math.sin(v), POD_PROFILE_EXP)))
    bottom, top = len(verts), len(verts) + 1
    verts += [(0, 0, z0 - POD_BOTTOM), (0, 0, z0 + POD_TOP)]
    for j in range(nv - 2):
        for i in range(nu):
            a, b = j * nu + i, j * nu + (i + 1) % nu
            faces.append((a, b, b + nu, a + nu))
    for i in range(nu):
        faces.append((bottom, (i + 1) % nu, i))
        faces.append((top, (nv - 2) * nu + i, (nv - 2) * nu + (i + 1) % nu))
    return mesh_object("pod", verts, faces, subsurf=1)


def cylinder(name, r, depth, loc, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    if bevel:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width, mod.segments = bevel, 4
    return obj


def emission_material(name, rgb, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def main():
    clear_scene()
    top_z = WRIST_RZ + STRAP_T / 2
    z0 = top_z + POD_BOTTOM - 0.12          # pod sits slightly into the strap
    pod(z0)

    lens_top = z0 + POD_TOP + 0.015
    cylinder("lens", LENS_R, 0.3, (0, 0, lens_top - 0.15), bevel=0.04)

    # clock face on the lens: two hands and a centre dot, lit from inside
    hand_mat = emission_material("UI hands", (0.95, 0.93, 0.88), 3.0)
    for name, length, angle, width in (("hand_hour", 0.55, 120, 0.09), ("hand_min", 0.85, 0, 0.06)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, lens_top + 0.002))
        h = bpy.context.active_object
        h.name = name
        h.scale = (length, width, 0.004)
        a = math.radians(angle)
        h.location.x, h.location.y = math.cos(a) * length / 2, math.sin(a) * length / 2
        h.rotation_euler.z = a
        h.data.materials.append(hand_mat)
    dot = cylinder("pin_centre", 0.08, 0.01, (0, 0, lens_top + 0.006))

    # side button, a soft pill on the +Y flank
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1,
                                         location=(0, -POD_W / 2 - 0.02, z0 + 0.2))
    btn = bpy.context.active_object
    btn.name = "button"
    btn.scale = (0.5, 0.14, 0.16)
    bpy.ops.object.shade_smooth()

    # strap: one closed loop (the overlap of pin-and-tuck is left out at concept stage)
    sweep("strap", 0, 2 * math.pi, 240, STRAP_W, STRAP_T, closed=True)
    # keeper loop on the lower left
    sweep("keeper", math.radians(208), math.radians(224), 16, STRAP_W + 0.18, STRAP_T + 0.22)
    # adjustment holes (dark recesses) and the sunny pin on the lower right
    for k in range(6):
        t = math.radians(338 + k * 7.5)
        (x, z), (nx, nz) = band_frame(t)
        ang = math.atan2(nx, nz)
        r = STRAP_T / 2
        if k == 2:
            cylinder("pin", 0.13, 0.12, (x + nx * (r + 0.03), 0, z + nz * (r + 0.03)), rot=(0, ang, 0), bevel=0.03)
        else:
            hole = cylinder("hole_%d" % k, 0.12, 0.06, (x + nx * (r - 0.02), 0, z + nz * (r - 0.02)), rot=(0, ang, 0))
            mat = bpy.data.materials.get("hole") or bpy.data.materials.new("hole")
            mat.diffuse_color = (0.02, 0.02, 0.02, 1)
            mat.use_nodes = True
            mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.03, 0.03, 0.035, 1)
            hole.data.materials.append(mat)
    print("Pebble blockout built")


main()
