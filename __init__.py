import os
import bpy

from . import interface, operators

bl_info = {
    "name": "Archicad exporter",
    "author": "Clovis Flayols",
    "version": (0, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Toolshelf",
    "description": "Archicad object automatic creation. With a bit of luck.",
    "category": "Export",
}


class archicad_exporter(bpy.types.AddonPreferences):
    bl_idname = __package__

    LP_XMLConverter: bpy.props.StringProperty(
        name= "LP_XMLConverter", 
        description="LP_XMLConverter.exe is located in archicad installation folder.", 
        default="C:\\Program Files\\GRAPHISOFT\\ARCHICAD 25\\LP_XMLConverter.exe", 
        subtype="FILE_PATH")

    def draw(self, context):
        layout = self.layout.row()
        layout.prop(self, "LP_XMLConverter")

def register():
    bpy.utils.register_class(archicad_exporter)
    operators.register()
    interface.register()

def unregister():
    operators.unregister()
    interface.unregister()
    bpy.utils.unregister_class(archicad_exporter)

if __name__ == "__main__":
    register()
