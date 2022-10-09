import bpy
import subprocess
import os

class export_properties(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty(name="Object name", default="Object")
    is_placable: bpy.props.BoolProperty(default=True, description="Will the object be viewable in search popup")
    smooth_angle: bpy.props.FloatProperty(name="smooth angle", default=1.0, subtype="ANGLE")
    save_path: bpy.props.StringProperty(name="save to", subtype="DIR_PATH", default="C:\\Users\\Asloric\\Desktop\\")
    export_lod: bpy.props.BoolProperty(name="export as LOD", default=False)
    lod_1: bpy.props.PointerProperty(name="Coarse", type=bpy.types.Object)
    lod_0: bpy.props.PointerProperty(name="Detailed", type=bpy.types.Object)

    def register():
        bpy.types.Scene.acaccf = bpy.props.PointerProperty(type=export_properties)
    
    def unregister():
        del bpy.types.Scene.acaccf


class ACACCF_OT_export(bpy.types.Operator):
    bl_idname = "acaccf.export"
    bl_label = "export"

    def draw(self, context):
        prop = context.scene.acaccf
        layout = self.layout
        layout.prop(prop, "export_lod")
        layout.prop(prop, "object_name")
        layout.prop(prop, "lod_0", text="Detailed" if prop.export_lod else "Model")
        if prop.export_lod:
            layout.prop(prop, "lod_1")
        layout.separator(factor=1)
        layout.prop(prop, "save_path")
        layout.separator(factor=1)
        layout.prop(prop, "smooth_angle")
        if not prop.export_lod:
            layout.prop(prop, "is_placable")

    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        props = context.scene.acaccf
        from . import mesh_to_gdl, mesh_to_symbol, xml_template, xml_lod
        
        def process_object(props, lod, is_placable, lod_number= None):
            if lod_number is not None:
                object_name = lod.name + "_LOD" + str(lod_number)
            else:
                object_name = props.object_name
            bpy.context.view_layer.objects.active = lod

            # Duplicate selected object
            bpy.ops.object.duplicate(linked=False)

            # get object dimensions
            size_x = context.active_object.dimensions.x
            size_y = context.active_object.dimensions.y
            size_z = context.active_object.dimensions.z

            # Ensure edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            # select all
            bpy.ops.mesh.select_all(action='SELECT')

            # split non-planar faces (1°)
            bpy.ops.mesh.vert_connect_nonplanar(angle_limit=0.0174533)

            # create 2d script
            #bpy.context.scene.render.engine = 'CYCLES'
            #symbol_script = mesh_to_symbol.run_script(self.save_path)

            # create 3d script
            mesh_script = mesh_to_gdl.run_script(props.smooth_angle, texture_folder)
            
            #get back to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # complete xml
            xml = xml_template.get_xml(is_placable, "PROJECT2{2} 3, 90, 288", mesh_script, size_x, size_y, size_z, lod_number, ac_version)


            target_filepath = props.save_path + object_name + ".xml"
            print("writing file...")
            with open(target_filepath, 'w') as target_file:
                target_file.write(xml)
            print("file saved to " + target_filepath)

            return (size_x, size_y, size_z)

        def process_lod_xml(props, object_dimensions, ac_version):
           
            # complete xml
            xml = xml_lod.get_xml(props.object_name, props.is_placable, object_dimensions[0], object_dimensions[1], object_dimensions[2], ac_version)


            target_filepath = props.save_path + props.object_name + ".xml"
            print("writing file...")
            with open(target_filepath, 'w') as target_file:
                target_file.write(xml)
            print("file saved to " + target_filepath)

        # Create textures folder
        texture_folder = props.save_path + "textures\\"
        if not os.path.exists(props.save_path + "textures\\"):
            os.mkdir(texture_folder)


        # get lp_xmlconverter path
        preferences = bpy.context.preferences.addons[__package__].preferences
        lp_xmlconverter_path = preferences.LP_XMLConverter
        ac_version = preferences.ac_version
        
        # Process the meshed if lod or single
        if props.export_lod and props.lod_0 and props.lod_1:
            i = 0
            for lod in [props.lod_0, props.lod_1]:
                object_dimensions = process_object(props, lod, False, i)
                i += 1
            process_lod_xml(props, object_dimensions, ac_version)
        else:
            # Ensure at lease one object is being submitted to the process function
            lod = props.lod_1 if props.lod_1 else props.lod_0
            lod = context.active_object if not lod else lod
            process_object(props, lod, props.is_placable, None)
            

        subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', shell=True)

        bpy.ops.object.delete(use_global=True, confirm=False)

        return{'FINISHED'}

    def invoke(self, context, event):
        props = context.scene.acaccf

        # If multiple objects are selected, switch to lod mode. Assign lods based on face count.
        if len(context.selected_objects) > 1:
            obj_a = context.selected_objects[0]
            obj_b = context.selected_objects[1]

            if len(obj_a.data.polygons) < len(obj_b.data.polygons):
                props.lod_0 = obj_b
                props.lod_1 = obj_a
            else:
                props.lod_0 = obj_a
                props.lod_1 = obj_b
        else:
            props.lod_0 = context.active_object
        
        if not props.object_name:
            # Set the blender's file name as object name. 
            props.object_name = bpy.path.basename(bpy.context.blend_data.filepath)
            
        return context.window_manager.invoke_props_dialog(self)

classes = [
    ACACCF_OT_export,
    export_properties
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
