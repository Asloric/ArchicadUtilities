# interface.py - Blender UI panel definitions for the Archicad Converter addon.
#
# Registers four sub-panels nested under a shared header panel in the 3D Viewport N-panel
# (the sidebar opened with N key). All panels appear under the "AC ▣" tab category.
#
# Panel hierarchy (bl_parent_id links):
#   ACACCF_PT_Main      (header, bl_order=0)  — container with no own UI
#   ├── ACACCF_PT_Cleanup    (bl_order=0)     — mesh prep operators
#   ├── ACACCF_PT_Properties (bl_order=1)     — Archicad parameter list + editor
#   └── ACACCF_PT_Export     (bl_order=2, no parent) — export settings + trigger
#
# NOTE: ACACCF_PT_Export does NOT declare bl_parent_id, so it appears as a sibling
# of the header panel rather than a child. This may be intentional (keeps Export
# visually separate) or an oversight.

import bpy
import os
from . import properties

class ACACCF_PT_Main(bpy.types.Panel):
    """Top-level container panel. Has no UI of its own — acts as parent for sub-panels.
    The commented-out ensure_default_props call was an earlier initialisation strategy,
    now handled by the load_post handler in properties.py instead."""
    bl_label = "Archicad Converter"
    bl_idname = "AC_PT_HEADER"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AC ▣"
    bl_description = "export object to archicad"
    bl_context = "objectmode"
    bl_order = 0

    def draw(self, context):
        layout = self.layout.column(align=False)
        # if not len(context.scene.archicad_converter_props.collection):
        #     properties.AC_PropertyGroup_props.ensure_default_props(context.scene.archicad_converter_props, context)


class ACACCF_PT_Cleanup(bpy.types.Panel):
    """Mesh preparation panel. Operators here must be run BEFORE export.
    'APPLY ALL' runs ACACCF_OT_apply (applies modifiers, joins meshes, optionally bakes LOD).
    The three mesh-cleaning operators (remove_doubles, delete_loose, connect_coplanar)
    map to ACACCF_OT_remove_doubles, ACACCF_OT_delete_loose, ACACCF_OT_connect_coplanar
    in operators.py. 'apply transform' uses the built-in Blender operator."""
    bl_label = "Cleanup"
    bl_idname = "AC_PT_CLEANUP"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AC ▣"
    bl_description = "Clean up object"
    bl_context = "objectmode"
    bl_order = 0
    bl_parent_id = "AC_PT_HEADER"

    def draw(self, context):
        layout = self.layout.column(align=False)
        layout.operator("acaccf.apply", text="APPLY ALL")

        layout.separator()

        t_apply = layout.operator("object.transform_apply", text="apply transform")
        t_apply.location = True
        t_apply.rotation = True
        t_apply.scale = True

        layout.operator("acaccf.remove_doubles", text="remove doubles")
        layout.operator("acaccf.delete_loose", text="delete loose")
        layout.operator("acaccf.connect_coplanar", text="connect coplanar")


class ACACCF_PT_Properties(bpy.types.Panel):
    """Archicad parameter list and per-parameter editor.

    Upper section: template_list renders the AC_UL_props UIList (defined in properties.py),
    showing all parameters in archicad_converter_props.collection. Side buttons add/remove
    parameters and move them up/down in the list.

    Lower section (shown only when a parameter is selected):
      - Flag row: hide / child / bold / unique toggles (icons map to Archicad ParFlg_* flags)
      - For mandatory system parameters (pen/line/fill): shows type and name as labels (non-editable)
      - For user parameters: shows editable type, name, and value fields
      - `bottom_part.prop(prop, prop.ac_type, text="Value")`: dynamically selects the
        correct value field by using the ac_type string as the attribute name
        (e.g. ac_type="Length" → prop.Length)
    """
    bl_label = "Properties"
    bl_idname = "AC_PT_PROPERTIES"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AC ▣"
    bl_description = "export object to archicad"
    bl_context = "objectmode"
    bl_order = 1
    bl_parent_id = "AC_PT_HEADER"

    def draw(self, context):
        layout = self.layout.column(align = False)

        top_part = layout.row(align = False)
        top_part.template_list("AC_UL_props", "", bpy.context.scene.archicad_converter_props, "collection", bpy.context.scene.archicad_converter_props, "active_user_index")

        buttons_col = top_part.column(align=True)
        buttons_col.operator("acaccf.property_add", icon="ADD", text="")
        buttons_col.operator("acaccf.property_remove", icon="REMOVE", text="")
        buttons_col.separator()

        buttons_col.operator("acaccf.property_up", icon="TRIA_UP", text="")
        buttons_col.operator("acaccf.property_down", icon="TRIA_DOWN", text="")


        prop_group = bpy.context.scene.archicad_converter_props

        if len(prop_group.collection) and prop_group.active_user_index < len(prop_group.collection):
            prop = prop_group.collection[prop_group.active_user_index]

            # Flag row: icons change to reflect current flag state.
            flags = layout.row(align = False)
            flags.prop(prop, "hide_flag", emboss=False, text="", icon="HIDE_ON" if prop.hide_flag else "HIDE_OFF")
            flags.prop(prop, "child_flag", text="", icon="CON_CHILDOF")
            flags.prop(prop, "bold_flag", text="", icon="BOLD")
            flags.prop(prop, "unique_flag", text="", icon="EVENT_U")

            bottom_part = layout.column(align=False)
            bottom_part.use_property_split = True
            bottom_part.use_property_decorate = False
            bottom_part.alignment = "RIGHT"

            # Mandatory system parameters: show fixed labels (type and name are not user-editable).
            if prop.identifier in ["PenAttribute_1", "lineTypeAttribute_1", "fillAttribute_1", "fillbgpen_1", "fillfgpen_1"]:
                line = bottom_part.row()
                line.label(text= "")
                line.label(text=prop.ac_type)
                line = bottom_part.row()
                line.label(text="")
                line.label(text=prop.name)
            else:
                # User parameters: fully editable type, name, and value.
                bottom_part.prop(prop, "ac_type", text="Type")
                bottom_part.prop(prop, "name", text="Name")

            # Dynamic value field: prop.ac_type (e.g. "Length") names the attribute to display.
            bottom_part.prop(prop, prop.ac_type, text="Value")

class ACACCF_PT_Export(bpy.types.Panel):
    """Export settings and trigger panel.

    Shows fields from scene.acaccf (AC_export_properties):
      - object_name: the .gsm filename (no extension)
      - save_path: output directory
      - export_lod: toggle for LOD export mode
        - When True: shows both lod_0 (detailed) and lod_1 (coarse) object pickers
        - When False: shows only lod_0 as "Model", hides is_placable (LOD objects are not placeable)
      - smooth_angle: dihedral angle threshold for smooth vs hard edge in GDL
      - is_placable: controls AC XML IsPlaceable attribute (hidden in LOD mode)

    NOTE: This panel has no bl_parent_id, so it renders as a top-level sibling of
    ACACCF_PT_Main rather than a nested child, even though logically it belongs to the
    same workflow group.
    """
    bl_label = "Export"
    bl_idname = "AC_PT_EXPORT"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AC ▣"
    bl_description = "export object to archicad"
    bl_context = "objectmode"
    bl_order = 2

    def draw(self, context):
        prop = context.scene.acaccf

        layout = self.layout

        layout.prop(prop, "object_name")
        layout.prop(prop, "save_path")
        layout.separator(factor=1)

        layout.prop(prop, "export_lod")
        # Label changes: "Detailed" in LOD mode, "Model" in single-object mode.
        layout.prop(prop, "lod_0", text="Detailed" if prop.export_lod else "Model")
        if prop.export_lod:
            layout.prop(prop, "lod_1")
        layout.separator(factor=1)

        layout.prop(prop, "smooth_angle")
        if not prop.export_lod:
            layout.prop(prop, "is_placable")

        layout.operator("acaccf.export", text="Export object")


classes = [
    ACACCF_PT_Main,
    ACACCF_PT_Cleanup,
    ACACCF_PT_Properties,
    ACACCF_PT_Export,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
