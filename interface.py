import bpy
import os
from . import properties

class ACACCF_PT_Main(bpy.types.Panel):
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
        if not len(context.window_manager.archicad_converter_props.collection):
            properties.AC_PropertyGroup_props.ensure_default_props(context.window_manager.archicad_converter_props, context)

            
class ACACCF_PT_Cleanup(bpy.types.Panel):
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
        top_part.template_list("AC_UL_props", "", bpy.context.window_manager.archicad_converter_props, "collection", bpy.context.window_manager.archicad_converter_props, "active_user_index")

        buttons_col = top_part.column(align=True)
        buttons_col.operator("acaccf.property_add", icon="ADD", text="")
        buttons_col.operator("acaccf.property_remove", icon="REMOVE", text="")
        buttons_col.separator()

        buttons_col.operator("acaccf.property_up", icon="TRIA_UP", text="")
        buttons_col.operator("acaccf.property_down", icon="TRIA_DOWN", text="")

        
        prop_group = bpy.context.window_manager.archicad_converter_props

        if len(prop_group.collection) and prop_group.active_user_index < len(prop_group.collection):
            prop = prop_group.collection[prop_group.active_user_index]

            flags = layout.row(align = False)
            flags.prop(prop, "hide_flag", emboss=False, text="", icon="HIDE_ON" if prop.hide_flag else "HIDE_OFF")
            flags.prop(prop, "child_flag", text="", icon="CON_CHILDOF")
            flags.prop(prop, "bold_flag", text="", icon="BOLD")
            flags.prop(prop, "unique_flag", text="", icon="EVENT_U")


            bottom_part = layout.column(align=False)
            bottom_part.use_property_split = True
            bottom_part.use_property_decorate = False
            bottom_part.alignment = "RIGHT"
            


            if prop.identifier in ["PenAttribute_1", "lineTypeAttribute_1", "fillAttribute_1"]:
                if prop.identifier == "PenAttribute_1":
                    line = bottom_part.row()
                    line.label(text= "")
                    line.label(text= "Pen Color")
                else:
                    line = bottom_part.row()
                    line.label(text= "")
                    line.label(text= "Line Type")
                line = bottom_part.row()
                line.label(text="") 
                line.label(text=prop.name) 

            else:
                bottom_part.prop(prop, "ac_type", text="Type")
                bottom_part.prop(prop, "name", text="Name")
            
            bottom_part.prop(prop, prop.ac_type, text="Value")

class ACACCF_PT_Export(bpy.types.Panel):
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
