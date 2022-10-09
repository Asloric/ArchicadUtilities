import bpy
import os

class ACACCF_PT_Main(bpy.types.Panel):
    bl_label = "AGENCE CARRE"
    bl_idname = "ACACCF_PT_HEADER"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AC CF"
    bl_description = "export object to archicad"
    bl_context = "objectmode"


    def draw(self, context):
        layout = self.layout.column(align=False)
        layout.operator("acaccf.export", text="Export object")
        


classes = [
    ACACCF_PT_Main,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
