"""Export cmf.json as a spec table (CSV) or as a filled Vizcom render prompt.

    python3 scripts/cmf_export.py cmf/cmf.json --csv [--colorway B] > spec.csv
    python3 scripts/cmf_export.py cmf/cmf.json --prompt [--colorway B]
"""
import argparse
import csv
import json
import sys


def resolve(cmf, colorway):
    overrides = cmf.get("colorways", {}).get(colorway, {}) if colorway else {}
    if colorway and colorway not in cmf.get("colorways", {}):
        sys.exit(f"unknown colourway {colorway!r}")
    for line in cmf["cmf"]:
        code = overrides.get(line["code"], line["color"])
        yield line, code, cmf["colors"][code], cmf["materials"][line["material"]], cmf["finishes"][line["finish"]]


def write_csv(cmf, colorway):
    out = csv.writer(sys.stdout)
    out.writerow(["CMF", "Part", "Material", "Process", "Colour code", "Colour", "Hex", "Reference", "Finish code", "Finish"])
    for line, code, color, material, finish in resolve(cmf, colorway):
        out.writerow([line["code"], line["part"], material["name"], material.get("process", ""), code,
                      color["name"], color["hex"], color.get("ref", ""), line["finish"], finish["name"]])


def write_prompt(cmf, colorway):
    parts = "; ".join(f"{line['part'].lower()}: {color['name'].lower()} {material['name']}, {finish['name']}"
                      for line, code, color, material, finish in resolve(cmf, colorway))
    print(f"Photorealistic product render, {cmf['product']}, studio photography, seamless light grey backdrop, "
          f"soft key light from upper left, subtle floor reflection, three-quarter view. {parts}. "
          f"Crisp parting lines, realistic injection-moulded plastic, no logos, no text.")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cmf")
    p.add_argument("--colorway")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--csv", action="store_true")
    g.add_argument("--prompt", action="store_true")
    a = p.parse_args()
    with open(a.cmf, encoding="utf-8") as f:
        cmf = json.load(f)
    (write_csv if a.csv else write_prompt)(cmf, a.colorway)


if __name__ == "__main__":
    main()
