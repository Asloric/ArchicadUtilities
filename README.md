# Overview

This project is a **Blender addon** that exports Blender meshes to **Archicad library parts** (`.gsm`).

This allows fully contained objects with textures and preview embbed.
An optionnal LOD system (depecated because of library maintenance complexity)

The export pipeline produces:

- a **3D GDL script** generated from the Blender mesh,
- a **2D GDL symbol** generated from the object top view,
- an **Archicad XML descriptor** containing scripts, parameters, materials, textures, and metadata,
- optionally an **LOD wrapper object** that switches between detailed and simplified variants.

The XML output is compiled into `.gsm` files by **LP_XMLConverter.exe**, which is installed with Archicad and configured in the addon preferences.

---

## 1. Repository Structure

```
ArchicadUtilitiesTest/
├── __init__.py                  # Addon entry point, preferences, version codes
├── operators.py                 # All Blender operators (the export pipeline)
├── mesh_to_gdl.py               # 3D GDL script generator
├── mesh_to_symbol.py            # 2D symbol generator (WIP, BVH approach)
├── xml_template.py              # Single-object Archicad XML builder
├── xml_lod.py                   # LOD wrapper XML builder
├── properties.py                # Blender property groups (UI data model)
├── interface.py                 # Blender UI panels (4 panels in the N-panel sidebar)
├── utils.py                     # String sanitisation helpers
├── local_dict.py                # GDL reserved keyword list (used by utils.cleanString)
└── standalone_scripts/
    ├── 3D optimiser.py          # GDL text-file TEVE/EDGE deduplicator
    ├── Replace line type.py     # Batch edge status replacer
    ├── poly2 to 3.py            # poly2_b{5} → poly_ command converter
    ├── compile_textures_to_objects.py  # Embed surfaces into object XMLs
    ├── mesh_to_symbol.py        # OLD 2D symbol generator (Freestyle SVG — superseded by mesh_to_symbol_new.py)
    └── Tiff_to_xyz.py           # GeoTIFF → XYZ terrain point cloud
```

### Main addon files

- `__init__.py` — addon metadata, preferences, registration wiring
- `interface.py` — Blender UI panels shown in the 3D View sidebar
- `operators.py` — cleanup/export operators and the main export pipeline
- `properties.py` — scene properties, parameter model, default parameter maintenance
- `mesh_to_gdl.py` — 3D GDL generator from Blender mesh data
- `mesh_to_symbol.py` — 2D symbol generator from processed top-view geometry
- `xml_template.py` — XML builder for a normal exported object
- `xml_lod.py` — XML builder for the LOD wrapper object
- `utils.py` — identifier sanitization helpers
- `local_dict.py` — GDL reserved keyword list used by `utils.py`

### `3D optimiser.py`
**Purpose:** Text-file predecessor to the TEVE/EDGE class logic in `mesh_to_gdl.py`.
Reads a GDL `.txt` file, deduplicates `TEVE` vertices and `EDGE` entries using O(n²) nested loops, then writes a cleaned version. Functionally equivalent to `mesh_to_gdl.py`'s dedup logic but operates on GDL rather than Blender mesh data.
**Note:** Using soft edges (`status=2` on EDGE) makes objects invisible in Archicad's sketch rendering mode.

### `poly2 to 3.py`
**Purpose:** Converts Archicad 2D GDL script to 3D shape.
Convert `poly2_b{5}` 2D GDL commands to `poly_` format.


### `compile_textures_to_objects.py`
**Purpose:** Embed Archicad surface definitions (materials + textures) directly into object XML files, making objects self-contained and portable across projects.
- For each Material parameter in an object, embeds the full `DEFINE MATERIAL`/`DEFINE TEXTURE` GDL block into `Script_1D` and copies texture files as `GDLPict` entries.
- Adds a GDL override block in `Script_3D` so users can still replace the embedded surface inside Archicad.

### `Tiff_to_xyz.py`
**Purpose:** Convert a GeoTIFF heightmap to an XYZ point cloud for Archicad terrain import.
Uses edge detection (Gaussian blur diff) to output high-detail points at terrain feature edges, plus a sparse grid for base coverage. Hardcoded input/output paths.

---

## 2. Export Pipeline

```
(Optional) User clicks "Apply all" in Blender
        │
        ▼
ACACCF_OT_apply (operators.py)
  - Apply modifiers
  - Join all selected objects into one mesh
  - Optionally bake a coarse LOD variant (SubSurf level=0)
        │
        ▼
User clicks "Export" in Blender
        │
        ▼
ACACCF_OT_export (operators.py) — 7 steps:
  1. Triangulate mesh
  2. mesh_to_gdl.run_script()        → GDL 3D script string
  3. mesh_to_symbol.run_script()     → GDL 2D symbol string
  4. xml_template.run_script()       → Archicad XML string
  5. Write .xml + texture folder to disk
  6. Call LP_XMLConverter.exe        → converts XML to .gsm
  7. If LOD: xml_lod.run_script()    → LOD wrapper XML → LP_XMLConverter.exe
```

---
# Technical workflow

## 3. GDL Geometry Generation (`mesh_to_gdl.py`, `mesh_to_symbol.py`)

The core of the addon. Converts a Blender triangulated mesh into Archicad GDL 2D and 3D geometry commands.

**Key GDL commands produced:**
| Command | Description |
|---------|-------------|
| `TEVE x, y, z, u, v` | Texture vertex (position + UV) |
| `EDGE v1, v2, f1, f2, status` | Directed edge between two vertices |
| `PGON n, vect, status, e1, e2, e3` | Triangle polygon referencing 3 edges |
| `BODY -1` / `BODY 0` | End of mesh body |
| `DEFINE MATERIAL` | Material definition |
| `DEFINE TEXTURE` | Texture definition |

**Deduplication strategy (O(1)):**
- `TEVE`: keyed by `(x, y, z, u, v)` tuple in a dict. Returns existing index on collision.
- `EDGE`: keyed by `(v1, v2)`. Reversed edges `(v2, v1)` return a negative index (Archicad GDL mirror convention).

**Per-material BODY loop:** One `BODY` group is emitted per material slot, so Archicad can apply different building material to different parts of the mesh.

**Surface override pattern:** For each material, the GDL checks a user parameter:
```gdl
IF sf_<name> = 0 THEN
    SET MATERIAL "material_<name>"
ELSE
    SET MATERIAL sf_<name>
ENDIF
```
This lets the user override surfaces inside Archicad without re-exporting.

---

## 4. 2D Symbol Generation (`mesh_to_symbol.py`)

Uses BVH to generate a top-view silhouette:

1. Cast rays downward from a grid of points above the object.
2. Collect hit faces — these are the visible faces in plan view.
3. Merge coplanar faces, dissolve near-collinear edges.
4. Filter faces by restrictive visibility (remove faces fully occluded by others).
5. **TODO:** Convert resulting mesh to GDL `POLY2` / `POLY2_B` commands. (Not implemented.)

The function `run_script(start_obj)` currently returns `None`.

**Old approach** (`_old_mesh_to_symbol.py`, superseded): Used Blender's Freestyle SVG renderer to render silhouette lines, then imported the SVG back as curves and converted to GDL. This implementation did return a GDL string. It was replaced but the operator call was not updated (see Bug #1 below). TODO: allow user to choose between new, old, and archicad's 2D generation (project2 command)

---

## 5. XML / GSM Output (`xml_template.py`, `xml_lod.py`)

`xml_template.py` produces the Archicad XML format consumed by LP_XMLConverter.exe. Key sections:
- **ParamSection**: parameter definitions (type, flags, default value)
- **Script_1D**: property script (runs on library load; DEFINE MATERIAL, DEFINE TEXTURE)
- **Script_3D**: geometry script (GDL from mesh_to_gdl)
- **Script_2D**: 2D symbol script (GDL from mesh_to_symbol)
- **GDLPict**: embedded texture binary references

**LOD wrapper** (`xml_lod.py`): Creates a third `.gsm` that delegates to the LOD0 or LOD1 variant based on a `macro_choose` parameter, using a `macro[]` array: `macro[1]` and `macro[2]` = LOD1 (coarse), `macro[3]` = LOD0 (detailed).

---


# Planned Features

- Handle parametric GDL shapes from geometry nodes
- Handle modifiers as GDL code
- Support other object types: lights, doors, windows
- Auto-generate optimised 2D symbol (the current `mesh_to_symbol_new.py` is the WIP towards this)
- Self-shadow rendering for plan visualisation (ambient-occlusion-style, vectorial)
- Account for metadata (price, product reference)
- Mac support
- Version updater for objects created with older addon versions
- Let user choose between 2D generation method (Archicad's Project2, bitmap projection, geometric resolve)
- Add UI to use standalone scripts inside blender

