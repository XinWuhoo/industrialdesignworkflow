#! python3
"""Rhino 8: create a CMF::<code> layer with a physically based material for each line in cmf.json,
then move objects whose name matches a line's "match" patterns onto that layer.

Run from the ScriptEditor (Python 3). You are asked for cmf.json and an optional colourway.
Objects without a name, or with no match, stay where they are and are listed at the end:
move them onto the CMF layers by hand.
"""
import fnmatch
import json

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System


def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_material(name, color, material, finish):
    r, g, b = hex_to_rgb(color["hex"])
    mat = Rhino.DocObjects.Material()
    mat.Name = name
    mat.ToPhysicallyBased()
    pbr = mat.PhysicallyBased
    pbr.BaseColor = Rhino.Display.Color4f(r / 255.0, g / 255.0, b / 255.0, 1.0)
    pbr.Metallic = float(material.get("metallic", 0.0))
    pbr.Roughness = float(finish.get("roughness", 0.5))
    pbr.Opacity = 1.0 - float(material.get("transmission", 0.0))
    pbr.OpacityIOR = float(material.get("ior", 1.5))
    pbr.Clearcoat = float(finish.get("coat", 0.0))
    pbr.Sheen = float(finish.get("sheen", 0.0))
    return sc.doc.Materials.Add(mat), System.Drawing.Color.FromArgb(r, g, b)


def ensure_layer(full_name, color, material_index):
    parent_name, child_name = full_name.split("::")
    parent = sc.doc.Layers.FindName(parent_name)
    if parent is None:
        sc.doc.Layers.Add(parent_name, System.Drawing.Color.Black)
        parent = sc.doc.Layers.FindName(parent_name)
    idx = sc.doc.Layers.FindByFullPath(full_name, -1)
    if idx < 0:
        layer = Rhino.DocObjects.Layer()
        layer.Name = child_name
        layer.ParentLayerId = parent.Id
        idx = sc.doc.Layers.Add(layer)
    layer = sc.doc.Layers[idx]
    layer.Color = color
    layer.RenderMaterialIndex = material_index
    sc.doc.Layers.Modify(layer, idx, True)
    return idx


def main():
    path = rs.OpenFileName("cmf.json", "JSON (*.json)|*.json||")
    if not path:
        return
    with open(path, encoding="utf-8") as f:
        cmf = json.load(f)
    names = list(cmf.get("colorways", {}).keys())
    colorway = rs.ListBox(["(base)"] + names, "Colourway", "CMF") if names else None
    overrides = cmf["colorways"].get(colorway, {}) if colorway and colorway != "(base)" else {}

    lines = []
    for line in cmf["cmf"]:
        color_code = overrides.get(line["code"], line["color"])
        mat_idx, color = make_material(f"{line['code']} {line['material']} {color_code} {line['finish']}",
                                       cmf["colors"][color_code], cmf["materials"][line["material"]],
                                       cmf["finishes"][line["finish"]])
        layer_idx = ensure_layer(f"CMF::{line['code']} {line['part']}", color, mat_idx)
        lines.append((line, layer_idx))

    moved, unmatched = 0, []
    for obj in list(sc.doc.Objects):
        name = obj.Attributes.Name or ""
        hit = next((idx for line, idx in lines
                    if name and any(fnmatch.fnmatchcase(name.lower(), p.lower()) for p in line.get("match", []))), None)
        if hit is None:
            if name:
                unmatched.append(name)
            continue
        attrs = obj.Attributes.Duplicate()
        attrs.LayerIndex = hit
        attrs.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer
        sc.doc.Objects.ModifyAttributes(obj, attrs, True)
        moved += 1

    sc.doc.Views.Redraw()
    print(f"CMF: {len(lines)} layers, {moved} objects placed")
    if unmatched:
        print("CMF: unmatched named objects -> " + ", ".join(sorted(set(unmatched))))


main()
