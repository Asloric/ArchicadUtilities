# Archicad Utilities — Codebase Report

> Analysed February 2025. Covers all Python files in the repository.

---

## 1. What This Project Is

A **Blender addon** that exports 3D objects from Blender into Archicad library parts (`.gsm` files). The pipeline produces:

- A GDL 3D script (geometry)
- A GDL 2D symbol script (plan view)
- An Archicad XML descriptor with parameters, metadata, and embedded textures
- Optionally a Level-of-Detail (LOD) wrapper object

The output XML is converted to a `.gsm` binary by **LP_XMLConverter.exe**, an Archicad command-line tool that must be installed separately.

---

## 2. Repository Structure

```
ArchicadUtilitiesTest/
├── __init__.py                  # Addon entry point, preferences, version codes
├── operators.py                 # All Blender operators (the export pipeline)
├── mesh_to_gdl.py               # 3D GDL script generator
├── mesh_to_symbol_new.py        # 2D symbol generator (WIP, raycasting approach)
├── xml_template.py              # Single-object Archicad XML builder
├── xml_lod.py                   # LOD wrapper XML builder
├── properties.py                # Blender property groups (UI data model)
├── interface.py                 # Blender UI panels (4 panels in the N-panel sidebar)
├── utils.py                     # String sanitisation helpers
├── local_dict.py                # GDL reserved keyword list (used by utils.cleanString)
└── standalone_scripts/
    ├── 3D optimiser.py          # GDL text-file TEVE/EDGE deduplicator
    ├── Replace line type.py     # Batch edge status replacer
    ├── poly2 to 3.py            # poly2_b{5} → poly_ command converter
    ├── compile_textures_to_objects.py  # Embed surfaces into object XMLs
    ├── mesh_to_symbol.py        # OLD 2D symbol generator (Freestyle SVG — superseded by mesh_to_symbol_new.py)
    ├── calculatrice.py          # Desktop calculator (unrelated to addon)
    └── Tiff_to_xyz.py           # GeoTIFF → XYZ terrain point cloud
```

### Files That Are Part of the Addon

`__init__.py`, `operators.py`, `mesh_to_gdl.py`, `mesh_to_symbol_new.py`, `xml_template.py`, `xml_lod.py`, `properties.py`, `interface.py`, `utils.py`, `local_dict.py`

### Files That Are NOT Part of the Addon

All files in `standalone_scripts/`. These are run directly as Python scripts, have hardcoded paths, and have no `import` or function-call relationship to the addon.

---

## 3. Export Pipeline (main addon)

```
User clicks "Export" in Blender
        │
        ▼
ACACCF_OT_apply (operators.py)
  - Apply modifiers
  - Join all selected objects into one mesh
  - Optionally bake a coarse LOD variant (SubSurf level=0)
        │
        ▼
ACACCF_OT_export (operators.py) — 7 steps:
  1. Triangulate mesh
  2. mesh_to_gdl.run_script()        → GDL 3D script string
  3. mesh_to_symbol_new.run_script() → GDL 2D symbol string  ← WIP / broken
  4. xml_template.run_script()       → Archicad XML string
  5. Write .xml + texture folder to disk
  6. Call LP_XMLConverter.exe        → converts XML to .gsm
  7. If LOD: xml_lod.run_script()    → LOD wrapper XML → LP_XMLConverter.exe
```

---

## 4. GDL Geometry Generation (`mesh_to_gdl.py`)

The core of the addon. Converts a Blender triangulated mesh into Archicad GDL geometry commands.

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
- `EDGE`: keyed by `(v1, v2)`. Reversed edges `(v2, v1)` return a negative index (Archicad mirror convention).

**Per-material BODY loop:** One `BODY` group is emitted per material slot, so Archicad can apply different surfaces to different parts of the mesh.

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

## 5. 2D Symbol Generation (`mesh_to_symbol_new.py`)

**Status: Work in progress. Does not produce output yet.**

Uses Blender raycasting to generate a top-view silhouette:

1. Cast rays downward from a grid of points above the object.
2. Collect hit faces — these are the visible faces in plan view.
3. Merge coplanar faces, dissolve near-collinear edges.
4. Filter faces by restrictive visibility (remove faces fully occluded by others).
5. **TODO:** Convert resulting mesh to GDL `POLY2` / `POLY2_B` commands. (Not implemented.)

The function `run_script(start_obj)` currently returns `None`.

**Old approach** (`mesh_to_symbol.py`, superseded): Used Blender's Freestyle SVG renderer to render silhouette lines, then imported the SVG back as curves and converted to GDL. This implementation did return a GDL string. It was replaced but the operator call was not updated (see Bug #1 below).

---

## 6. XML / GSM Output (`xml_template.py`, `xml_lod.py`)

`xml_template.py` produces the Archicad XML format consumed by LP_XMLConverter.exe. Key sections:
- **ParamSection**: parameter definitions (type, flags, default value)
- **Script_1D**: property script (runs on library load; DEFINE MATERIAL, DEFINE TEXTURE)
- **Script_3D**: geometry script (GDL from mesh_to_gdl)
- **Script_2D**: 2D symbol script (GDL from mesh_to_symbol)
- **GDLPict**: embedded texture binary references

**GUID format:** `AC0000CF-0000-70D{lod}-{year}-00{mm}{dd}{HH}{MM}{SS}` — timestamp-based, ensuring uniqueness on each export. An `old_GUID` parameter can be set to preserve object identity across re-exports.

**LOD wrapper** (`xml_lod.py`): Creates a third `.gsm` that delegates to the LOD0 or LOD1 variant based on a `macro_choose` parameter, using a `macro[]` array: `macro[1]` and `macro[2]` = LOD1 (coarse), `macro[3]` = LOD0 (detailed).

---

## 7. UI Panels (`interface.py`)

Four `bpy.types.Panel` subclasses, all in the 3D Viewport N-panel sidebar under the **"AC ▣"** tab:

| Panel | `bl_idname` | Parent | Purpose |
|-------|-------------|--------|---------|
| `ACACCF_PT_Main` | `AC_PT_HEADER` | — | Container; no own UI |
| `ACACCF_PT_Cleanup` | `AC_PT_CLEANUP` | `AC_PT_HEADER` | Mesh prep operators |
| `ACACCF_PT_Properties` | `AC_PT_PROPERTIES` | `AC_PT_HEADER` | Parameter list + editor |
| `ACACCF_PT_Export` | `AC_PT_EXPORT` | — | Export settings + trigger |

**Cleanup panel:** Exposes `acaccf.apply` (the mandatory first step), Blender's built-in `object.transform_apply`, and three mesh cleanup operators (`remove_doubles`, `delete_loose`, `connect_coplanar`).

**Properties panel:** Renders the `AC_UL_props` UIList for the parameter collection. The per-parameter editor dynamically selects the value field with `layout.prop(prop, prop.ac_type)` — `prop.ac_type` is a string like `"Length"` which names the attribute to display. Mandatory system parameters (pen, line type, fill) are shown as non-editable labels.

**Export panel:** Binds to `scene.acaccf`. The `lod_0` label toggles between "Detailed" and "Model" depending on `export_lod`. `is_placable` is hidden in LOD mode (LOD components are not independently placeable). **Note:** this panel has no `bl_parent_id`, so it renders as a top-level sibling rather than a child of the header panel.

---

## 7a. GDL Keyword List (`local_dict.py`)

A single module-level list `gdl_keywords` containing all GDL reserved words. Used exclusively by `utils.cleanString()`: if a sanitised identifier matches any entry, the prefix `"bl_"` is prepended to avoid GDL parse errors. Covers the full GDL command set including control flow, math functions, string functions, 3D/2D geometry commands, transform commands, UI script commands, and operators.

---

## 8. Property System (`properties.py`)

Two property groups registered on `bpy.types.Scene`:

- **`scene.acaccf`** (`AC_export_properties`): export settings — object name, save path, smooth angle threshold, LOD object pointers.
- **`scene.archicad_converter_props`** (`AC_PropertyGroup_props`): user-defined Archicad parameters.

Each parameter (`AC_single_prop`) has:
- An `identifier` (GDL variable name, auto-sanitised and de-duplicated)
- A type from Archicad's parameter system (Length, Angle, Material, LineType, etc.)
- Flags mapping to Archicad XML `<Flags>`: hidden, child, bold, unique

**Mandatory parameters** always kept in the collection:
`PenAttribute_1`, `lineTypeAttribute_1`, `fillAttribute_1`, `fillbgpen_1`, `fillfgpen_1`, `product_reference`, `old_GUID`

---

## 8. Archicad Version Codes (`__init__.py`)

The `ac_version` enum uses Archicad internal format codes, not version numbers:

| Code | Archicad Version |
|------|-----------------|
| 40   | AC23            |
| 41   | AC24            |
| 43   | AC25            |
| 44   | AC26            |

Code 42 is skipped (no corresponding release). The default path references AC27 but AC27 is not yet in the enum.

---

## 9. Standalone Scripts

### `3D optimiser.py` (root) and `single scripts/3D optimiser.py`
**Purpose:** Text-file predecessor to the TEVE/EDGE class logic in `mesh_to_gdl.py`.
Reads a GDL `.txt` file, deduplicates `TEVE` vertices and `EDGE` entries using O(n²) nested loops, then writes a cleaned version. Functionally equivalent to `mesh_to_gdl.py`'s dedup logic but operates on raw text rather than Blender mesh data.

**These are two versions of the same script and are NOT identical:**
- The **root copy** is the correct, working version. It has the full `DO_IT()` function including the outer `for idx, vert in enumerate(vert_list):` loop.
- The **`single scripts/` copy** is broken: the outer loop is missing, leaving the inner loop at wrong indentation. This is a syntax error — the script cannot run.
- The root copy has anonymised paths (`Users\\x\\...`); `single scripts/` has a real username.

**Note:** Using soft edges (`status=2` on EDGE) makes objects invisible in Archicad's sketch rendering mode.

### `single scripts/Replace line type.py`
**Purpose:** Batch-replace the status value on all `EDGE` commands in a GDL `.txt` file.
**Bug:** The replacement call `line.replace(f", {replace_by}\n", f", {replace_by}\n")` replaces the string with an identical string — a no-op. The script reads and writes the file unchanged.

### `single scripts/poly2 to 3.py`
**Purpose:** Convert `poly2_b{5}` 2D GDL commands to `poly_` format.
Keeps only the vertex count argument and skips the following status/colour line. Used for porting 2D scripts between Archicad object types that expect different polygon command variants.

### `single scripts/compile_textures_to_objects.py`
**Purpose:** Embed Archicad surface definitions (materials + textures) directly into object XML files, making objects self-contained and portable across projects.
**Key techniques:**
- Monkey-patches `ET._serialize_xml` to preserve `<![CDATA[...]]>` sections that Python's `xml.etree.ElementTree` strips on parse.
- Three-class architecture: `SURFACES` (surface script data), `SURFACES_ATTRIBUTE` (index→name mapping), `OBJET` (object XML processor).
- For each Material parameter in an object, embeds the full `DEFINE MATERIAL`/`DEFINE TEXTURE` GDL block into `Script_1D` and copies texture files as `GDLPict` entries.
- Adds a GDL override block in `Script_3D` so users can still replace the embedded surface inside Archicad.

### `calculatrice.py`
**Purpose:** Standalone desktop calculator with persistent answer chaining (`ANS` variable). Compiled to `.exe` via PyInstaller. Completely unrelated to the Archicad addon.

### `Tiff_to_xyz.py`
**Purpose:** Convert a GeoTIFF heightmap to an XYZ point cloud for Archicad terrain import.
Uses edge detection (Gaussian blur diff) to output high-detail points at terrain feature edges, plus a sparse grid for base coverage. Hardcoded input/output paths.

---

## 10. Known Bugs

### Bug 1 — TypeError in 2D symbol export (operators.py ~line 294)
```python
# operators.py
mesh_to_symbol_new.run_script(props.save_path, start_obj=obj)
# mesh_to_symbol_new.run_script signature: run_script(start_obj)
```
The operator passes `props.save_path` as a positional argument, but the new function only accepts `start_obj`. This causes a `TypeError` every time 2D symbol export is attempted. The root cause: `mesh_to_symbol.py` (old) had signature `run_script(filepath, start_obj)`. When replaced by `mesh_to_symbol_new.py`, the signature was simplified but the operator call was not updated.

### Bug 2 — Walrus operator precedence (operators.py ~line 36)
```python
if camera_data := bpy.data.cameras.get("AC_Camera_3D") is not None:
```
Due to Python operator precedence, `:=` binds after `is not None`, so `camera_data` is assigned `True` or `False`, not the camera object. Camera operations on `camera_data` will fail.

### Bug 3 — 2D symbol returns None (`mesh_to_symbol_new.py`)
`run_script()` has no return statement that produces a GDL string. The 2D script section of the exported object will be empty.

### Bug 4 — Duplicate property definition (`properties.py` line 22)
`lod_0` is defined twice in `AC_export_properties`. The second definition silently overwrites the first in Python's class body. Harmless in practice (both definitions are identical) but indicates a copy-paste error.

### Bug 5 — No-op replacement (`single scripts/Replace line type.py` line 43)
```python
line.replace(f", {replace_by}\n", f", {replace_by}\n")
```
Source and target strings are identical. The file is written back unchanged.

### Bug 6 — Mirror modifier + merge vertices (per README)
Bad vertex references when the mirror modifier has "merge vertices" enabled. Not yet investigated in code.

---

## 11. Planned Features (per README)

- Handle parametric GDL shapes
- Support other object types: lights, doors, windows
- Auto-generate optimised 2D symbol (the current `mesh_to_symbol_new.py` is the WIP towards this)
- Self-shadow rendering for plan visualisation (ambient-occlusion-style, vectorial)
- Account for metadata (price, product reference)
- Mac support
- Version updater for objects created with older addon versions

---

## 12. Architecture Notes

- **Class-level state in `mesh_to_gdl.py`:** `TEVE` and `EDGE` use class-level lists and dicts. These must be explicitly cleared between calls via `TEVE.clear()` / `EDGE.clear()` or stale data from a previous export will contaminate the next.
- **`inspect.stack()` recursion guard (`properties.py`):** The `prop_enforce_name` callback guards against infinite recursion by checking call stack depth rather than a flag variable. Fragile but functional.
- **`exec()` in `compile_textures_to_objects.py`:** Used to append to a dynamically named list attribute on an instance. Could be replaced by `getattr(obj, tag).append(section)`.
- **French comments:** Much of the original code (especially `compile_textures_to_objects.py` and `mesh_to_symbol.py`) has comments in French. This report translates intent where relevant.
