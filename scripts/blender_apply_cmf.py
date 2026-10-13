"""Create Principled BSDF materials from cmf.json and assign them to objects by name.

Run from the command line:
    blender model.blend --python scripts/blender_apply_cmf.py -- cmf/cmf.json --colorway B

Or open this file in Blender's Scripting tab, set CMF_PATH below and press Run.
Objects are matched against each CMF line's "match" glob patterns (case-insensitive);
the first line that matches wins. Unmatched mesh objects are listed at the end.
"""
import fnmatch
import json
import sys

import bpy

CMF_PATH = "//cmf.json"   # used when no command-line path is given; "//" = next to the .blend
COLORWAY = None           # e.g. "B"; None keeps the base colours


def parse_args():
    path, colorway = CMF_PATH, COLORWAY
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if args and not args[0].startswith("--"):
            path = args.pop(0)
        if "--colorway" in args:
            colorway = args[args.index("--colorway") + 1]
    return bpy.path.abspath(path), colorway


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear_rgba(hex_str):
    h = hex_str.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)


def set_input(node, names, value):
    """Set the first input that exists; socket names differ between Blender 3.x and 4.x."""
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def build_material(name, color, material, finish):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    rgba = hex_to_linear_rgba(color["hex"])
    set_input(bsdf, ["Base Color"], rgba)
    set_input(bsdf, ["Metallic"], float(material.get("metallic", 0.0)))
    set_input(bsdf, ["IOR"], float(material.get("ior", 1.5)))
    set_input(bsdf, ["Transmission Weight", "Transmission"], float(material.get("transmission", 0.0)))
    set_input(bsdf, ["Roughness"], float(finish.get("roughness", 0.5)))
    set_input(bsdf, ["Coat Weight", "Clearcoat"], float(finish.get("coat", 0.0)))
    set_input(bsdf, ["Sheen Weight", "Sheen"], float(finish.get("sheen", 0.0)))

    bump_strength = float(finish.get("bump", 0.0))
    if bump_strength > 0:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-400, -200)
        noise.inputs["Scale"].default_value = 800.0  # fine grain; tune to model units
        bump = nodes.new("ShaderNodeBump")
        bump.location = (-150, -200)
        bump.inputs["Strength"].default_value = bump_strength
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    mat.diffuse_color = rgba  # viewport solid colour
    return mat


def main():
    path, colorway = parse_args()
    with open(path, encoding="utf-8") as f:
        cmf = json.load(f)
    overrides = cmf.get("colorways", {}).get(colorway, {}) if colorway else {}

    lines = []
    for line in cmf["cmf"]:
        color_code = overrides.get(line["code"], line["color"])
        name = f"{line['code']} {line['material']} {color_code} {line['finish']}"
        mat = build_material(name, cmf["colors"][color_code],
                             cmf["materials"][line["material"]], cmf["finishes"][line["finish"]])
        lines.append((line, mat))

    assigned, unmatched = 0, []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        hit = next((m for line, m in lines
                    if any(fnmatch.fnmatchcase(obj.name.lower(), p.lower()) for p in line.get("match", []))), None)
        if hit is None:
            unmatched.append(obj.name)
            continue
        obj.data.materials.clear()
        obj.data.materials.append(hit)
        assigned += 1

    print(f"CMF: {len(lines)} materials, {assigned} objects assigned, colourway {colorway or 'base'}")
    if unmatched:
        print("CMF: unmatched objects -> " + ", ".join(sorted(unmatched)))


main()
