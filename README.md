# Industrial design workflow

Concept → Rhino/Blender model → CMF → photoreal render → boards, with one CMF definition (`cmf/cmf.json`) used at every step.

The full workflow, the inputs and outputs for each step, the photoreal render standard and the CMF tokens live in the **CMF Pipeline** design system (Claude artifact).

## Files

| Path | What |
| --- | --- |
| `cmf/cmf.json` | Starter CMF definition: colours, materials, finishes, CMF lines, colourways. Copy it per project. |
| `scripts/blender_apply_cmf.py` | Blender: builds Principled BSDF materials from `cmf.json` and assigns them by object name. |
| `scripts/blender_photoreal_scene.py` | Blender: Cycles settings, sweep backdrop, three-point area lights, 85–135 mm camera. |
| `scripts/rhino_apply_cmf.py` | Rhino 8 (Python 3): a `CMF::` layer with a PBR material per CMF line; moves named objects onto them. |
| `scripts/cmf_export.py` | CMF spec table as CSV for boards, or a filled Vizcom prompt. |
| `projects/<name>/` | One folder per product: brief, cmf.json, concepts, model, renders, boards. |

## Quick start

```bash
# Blender: materials, then the studio scene, then render (F12)
blender model.blend --python scripts/blender_apply_cmf.py -- cmf/cmf.json --colorway A
blender model.blend --python scripts/blender_photoreal_scene.py -- --focal 100 --hdri studio.exr

# Spec table and Vizcom prompt
python3 scripts/cmf_export.py cmf/cmf.json --csv > spec.csv
python3 scripts/cmf_export.py cmf/cmf.json --prompt --colorway B
```

Name the parts in your model to match the `match` patterns in `cmf.json` (`housing_top`, `button_power`, `grille`…). The Blender and Rhino scripts have not yet been run against real models: run them on a copy of the file first.
