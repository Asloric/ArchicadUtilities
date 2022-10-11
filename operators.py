import bpy
import subprocess
import os
import shutil

def create_thumbnail(object, object_name, save_path):
    preferences = bpy.context.preferences.addons[__package__].preferences
    # Switch to scene
    current_scene = bpy.context.scene
    if not bpy.data.scenes.get("AC_render_scene"):
        bpy.ops.scene.new(type='NEW')
        new_scene = bpy.data.scenes[-1]
        new_scene.name = "AC_render_scene"
    
    render_scene = bpy.data.scenes.get("AC_render_scene")
    bpy.context.window.scene = render_scene

    # import object in scene
    render_scene.collection.objects.link(object)

    # if no camera, create one
    if not bpy.context.scene.camera:
        bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=(1.0738, 0.0130058, 1.16881), scale=(1, 1, 1))

    sun = False
    for ob in bpy.context.scene.objects:
        if ob.type == "LIGHT":
            sun = True

    if not sun:
        bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 0), rotation=(0.785398, 0.785398, -1.5708), scale=(1, 1, 1))

    bpy.context.scene.render.resolution_y = preferences.preview_resolution
    bpy.context.scene.render.resolution_x = preferences.preview_resolution

    if not bpy.context.scene.world:
        bpy.ops.world.new()
        bpy.context.scene.world = bpy.data.worlds[-1]

    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    bpy.context.scene.render.film_transparent = True


    # setup render
    filename = object_name + "_preview.png"
    filepath = save_path + "\\" + filename
    bpy.context.scene.render.filepath = filepath
    object.select_set(True)
    bpy.ops.view3d.camera_to_view_selected()
    bpy.context.scene.camera.data.clip_start = 0.000001

    bpy.ops.render.render(write_still=True)

    render_scene.collection.objects.unlink(object)
    bpy.context.window.scene = current_scene
        
class export_properties(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty(name="Object name", default="Object")
    is_placable: bpy.props.BoolProperty(default=True, description="Will the object be viewable in search popup")
    smooth_angle: bpy.props.FloatProperty(name="smooth angle", default=1.0, subtype="ANGLE")
    save_path: bpy.props.StringProperty(name="save to", subtype="DIR_PATH", default="C:\\Users\\Asloric\\Desktop\\")
    export_lod: bpy.props.BoolProperty(name="export as LOD", default=False)
    lod_1: bpy.props.PointerProperty(name="Coarse", type=bpy.types.Object)
    lod_0: bpy.props.PointerProperty(name="Detailed", type=bpy.types.Object)
    lod_0: bpy.props.PointerProperty(name="Detailed", type=bpy.types.Object)


    def register():
        bpy.types.Scene.acaccf = bpy.props.PointerProperty(type=export_properties)
    
    def unregister():
        del bpy.types.Scene.acaccf

class ACACCF_OT_apply(bpy.types.Operator):
    bl_idname = "acaccf.apply"
    bl_label = "Apply object"
    bl_description = "Apply modifiers and join objects. Mendatory step for proper export."

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        
        def apply_modifiers(obj):
            ctx = bpy.context.copy()
            ctx['object'] = obj
            for _, m in enumerate(obj.modifiers):
                try:
                    ctx['modifier'] = m
                    bpy.ops.object.modifier_apply(ctx, modifier=m.name)
                except RuntimeError:
                    print(f"Error applying {m.name} to {obj.name}, removing it instead.")
                    obj.modifiers.remove(m)

            for m in obj.modifiers:
                obj.modifiers.remove(m)
        

        # apply modifiers on every object in the selection
        bpy.ops.object.duplicate(linked=False)
        object_list = context.selected_objects
        active_object = context.active_object
        for obj in object_list:            
            apply_modifiers(obj)

        bpy.ops.object.join()


        return {"FINISHED"}


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
        
        def process_object(props, lod, is_placable, thumbnail_path, lod_number= None, ):
            if lod_number is not None:
                object_name = props.object_name + "_LOD" + str(lod_number)
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
            mesh_script, Textures_ids = mesh_to_gdl.run_script(props.smooth_angle, texture_folder)
            
            #get back to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Get the list of materials for AC override
            object_materials = []
            object_surfaces = []
            for material in lod.data.materials:
                if material:
                    object_materials.append(mesh_to_gdl.cleanString(material.name))
                    object_surfaces.append(f'sf_{mesh_to_gdl.cleanString(material.name)}')
            if not len(object_materials) > 0:
                object_materials = ["material_default"]
                object_surfaces = ["sf_material_default"]


            create_thumbnail(lod, props.object_name, thumbnail_path)


            # complete xml
            xml = xml_template.get_xml(props.object_name, is_placable, "PROJECT2{2} 3, 90, 51", mesh_script, size_x, size_y, size_z, lod_number, Textures_ids, object_surfaces, object_materials, ac_version, thumbnail_path=thumbnail_path)


            target_filepath = props.save_path + object_name + ".xml"
            print("writing file...")
            with open(target_filepath, 'w') as target_file:
                target_file.write(xml)
            print("file saved to " + target_filepath)

            bpy.ops.object.delete(use_global=True, confirm=False)
            return (size_x, size_y, size_z), object_materials, object_surfaces

        def process_lod_xml(props, object_dimensions, object_surfaces, object_materials, ac_version, thumbnail_path):
            # complete xml
            xml = xml_lod.get_xml(props.object_name, props.is_placable, object_dimensions[0], object_dimensions[1], object_dimensions[2], object_surfaces, object_materials,  ac_version, thumbnail_path=thumbnail_path)


            target_filepath = props.save_path + props.object_name + ".xml"
            print("writing file...")
            with open(target_filepath, 'w') as target_file:
                target_file.write(xml)
            print("file saved to " + target_filepath)

        # Create textures folder
        texture_folder = props.save_path + "textures"
        if not os.path.exists(props.save_path + "textures"):
            os.mkdir(texture_folder)



        # get lp_xmlconverter path
        preferences = bpy.context.preferences.addons[__package__].preferences
        lp_xmlconverter_path = preferences.LP_XMLConverter
        ac_version = preferences.ac_version
        
        # Process the meshed if lod or single
        if props.export_lod and props.lod_0 and props.lod_1:
            i = 0
            for lod in [props.lod_0, props.lod_1]:
                object_dimensions, object_materials, object_surfaces = process_object(props, lod, False, thumbnail_path=texture_folder, lod_number=i )


                subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart "{props.save_path + props.object_name}_LOD{str(i)}.xml" "{props.save_path + props.object_name}_LOD{str(i)}.gsm"', shell=True)
                i += 1
            create_thumbnail(props.lod_0, props.object_name, texture_folder)
            process_lod_xml(props, object_dimensions, object_surfaces, object_materials,  ac_version, thumbnail_path=texture_folder)
            subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart -img "{texture_folder}" "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', shell=True)
            
                #subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', shell=True)

        else:
            # Ensure at lease one object is being submitted to the process function
            lod = props.lod_0 if props.lod_0 else props.lod_1
            lod = context.active_object if not lod else lod
            process_object(props, lod, props.is_placable, thumbnail_path=texture_folder, lod_number=None )
            subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart -img "{texture_folder}" "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', shell=True)
                #subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', shell=True)
        
        #if os.path.exists(texture_folder):
        #    shutil.rmtree(texture_folder, ignore_errors=True)

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
                props.export_lod = True
            else:
                props.lod_0 = obj_a
                props.lod_1 = obj_b
                props.export_lod = True
        else:
            props.lod_0 = context.active_object
        
        if not props.object_name:
            # Set the blender's file name as object name. 
            props.object_name = bpy.path.basename(bpy.context.blend_data.filepath)
            
        return context.window_manager.invoke_props_dialog(self)

classes = [
    ACACCF_OT_export,
    export_properties,
    ACACCF_OT_apply
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
