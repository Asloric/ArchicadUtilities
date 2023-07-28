import os
import bpy

from . import interface, operators, properties

bl_info = {
    "name": "Archicad exporter",
    "author": "Clovis Flayols",
    "version": (1, 1, 0),
    "blender": (3, 3, 0),
    "location": "View3D > Toolshelf",
    "description": "Archicad object automatic creation. With a bit of luck.",
    "category": "Export",
}


class archicad_exporter(bpy.types.AddonPreferences):
    bl_idname = __package__

    LP_XMLConverter: bpy.props.StringProperty(
        name= "LP_XMLConverter", 
        description="LP_XMLConverter.exe is located in archicad installation folder.", 
        default="C:\\Program Files\\GRAPHISOFT\\ARCHICAD 24\\LP_XMLConverter.exe", 
        subtype="FILE_PATH")
    ac_version: bpy.props.EnumProperty(name="Archicad version", items=[
        ("40", "Archicad 23", "Archicad 23"), 
        ("41", "Archicad 24", "Archicad 24"), 
        ("43", "Archicad 25", "Archicad 25"),
        ("44", "Archicad 26", "Archicad 26"),
        ])
    camera_angle: bpy.props.FloatVectorProperty(name="icon camera angle", default=(1.222, 0.0, 0.523), unit='ROTATION', subtype="EULER")
    default_pen: bpy.props.IntProperty(name="default pen", default=5)
    default_line: bpy.props.IntProperty(name="default line", default=1)
    default_hatch: bpy.props.IntProperty(name="default line", default=21)
    default_surface: bpy.props.IntProperty(name="default surface", default=0)
    default_material: bpy.props.IntProperty(name="default material", default=0)
    preview_resolution: bpy.props.IntProperty(name="preview resolution", default=256)
    create_thumbnail: bpy.props.BoolProperty(name="Create thumbnail", description="Create preview image. Might take a few minutes", default=True)

    def draw(self, context):
        layout = self.layout.column()

        layout.prop(self, "camera_angle")


        layout.prop(self, "LP_XMLConverter")
        layout.prop(self, "ac_version")
        layout.prop(self, "default_pen", text="Stylo de contour")
        layout.prop(self, "default_line", text="Type de ligne")
        layout.prop(self, "default_hatch", text="Type de hachure")
        
        layout.prop(self, "default_surface", text="Surface de 3D")
        layout.prop(self, "default_material", text="Materiau de construction")
        layout.prop(self, "preview_resolution", text="Résolution de la preview")
        layout.prop(self, "create_thumbnail", text="générer preview automatique")

def register():
    bpy.utils.register_class(archicad_exporter)
    properties.register()
    operators.register()
    interface.register()

def unregister():
    operators.unregister()
    interface.unregister()
    properties.unregister()
    bpy.utils.unregister_class(archicad_exporter)

if __name__ == "__main__":
    register()
