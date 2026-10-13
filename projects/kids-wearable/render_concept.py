"""Build a concept blockout, apply CMF, set up the photoreal studio and render it.

    python render_concept.py <blockout.py> <cmf.json> <colourway> <out.png> [--res 1600x1200] [--samples 256] [--view 3q|top|wrist]

Runs inside Blender's Python (`blender --background --python-expr` or the `bpy` module).
"""
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector

REPO = Path(__file__).resolve().parents[2]

VIEWS = {  # camera direction from the product centre
    "3q": Vector((0.55, -0.9, 0.75)),
    "top": Vector((0.0, -0.25, 1.0)),
    "front": Vector((0.0, -1.0, 0.18)),
}


def run(path, argv):
    sys.argv = [str(path), "--"] + argv
    runpy.run_path(str(path), run_name="__main__")


def main(blockout, cmf, colorway, out, res="1600x1200", samples=256, view="3q", exposure=0.0):
    run(blockout, [])
    run(REPO / "scripts/blender_apply_cmf.py", [cmf] + (["--colorway", colorway] if colorway else []))
    run(REPO / "scripts/blender_photoreal_scene.py", ["--focal", "100"])
    scene = bpy.context.scene
    w, h = (int(v) for v in res.split("x"))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.cycles.samples = int(samples)
    scene.cycles.device = "CPU"
    scene.view_settings.exposure = float(exposure)
    # aim the camera at the pod, from the requested direction
    pod = bpy.data.objects["pod"]
    target = pod.matrix_world @ (sum((Vector(c) for c in pod.bound_box), Vector()) / 8)
    target.z -= 1.6
    cam = scene.camera
    dist = (cam.location - target).length * 1.3
    cam.location = target + VIEWS[view].normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = (cam.location - pod.location).length
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("rendered", out)


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    opts = {k.lstrip("-"): v for k, v in zip(a[4::2], a[5::2])}
    main(*a[:4], **opts)
