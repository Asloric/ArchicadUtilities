import bpy
import subprocess


class ACACCF_OT_export(bpy.types.Operator):
    bl_idname = "acaccf.export"
    bl_label = "export"

    object_name: bpy.props.StringProperty(name="Object name", default="Object")
    is_placable: bpy.props.BoolProperty(default=True, description="Will the object be viewable in search popup")
    ac_version: bpy.props.EnumProperty(name="Archicad version", items=[
        ("41", "Archicad 25", "Archicad 23"), 
        ("42", "Archicad 25", "Archicad 24"), 
        ("43", "Archicad 25", "Archicad 25"),
        ("44", "Archicad 25", "Archicad 26"),
        ])
    smooth_angle: bpy.props.FloatProperty(name="smooth angle", default=1.0, subtype="ANGLE")
    save_path: bpy.props.StringProperty(name="save to", subtype="DIR_PATH", default="C:\\Users\\Asloric\\Desktop\\")
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        from . import mesh_to_gdl, mesh_to_symbol, xml_template
        # Duplicate selected object
        bpy.ops.object.duplicate(linked=False)

        # get object dimensions
        size_x = context.active_object.dimensions.x
        size_y = context.active_object.dimensions.y
        size_z = context.active_object.dimensions.z

        # Ensure edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        # split non-planar faces (1°)
        bpy.ops.mesh.vert_connect_nonplanar(angle_limit=0.0174533)
        # create 3d script
        mesh_script = mesh_to_gdl.run_script(self.smooth_angle)
        # create 2d script
        # symbol_script = mesh_to_symbol.run_script(self.save_path)
        

        # complete xml
        xml = xml_template.get_xml(self.is_placable, "PROJECT2{2} 3, 90, 288", mesh_script, size_x, size_y, size_z, self.ac_version)

        #get back to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        target_filepath = self.save_path + self.object_name + ".xml"
        print("writing file...")
        with open(target_filepath, 'w') as target_file:
            target_file.write(xml)
        print("file saved to " + target_filepath)

        subprocess.call(f'"C:\\Program Files\\GRAPHISOFT\\ARCHICAD 25\\LP_XMLConverter.exe" xml2libpart "{target_filepath}" "{self.save_path + self.object_name}.gsm"', shell=True)
        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

classes = [
    ACACCF_OT_export
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
