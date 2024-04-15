import bpy
import subprocess
import os
from time import time
import shutil
from . import properties, utils

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

    # # if no camera, create one
    # if not bpy.context.scene.camera:
    #     bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=preferences.camera_angle, scale=(1, 1, 1))
    #     bpy.context.scene.camera.name = "AC_Camera_3D"
    # else:
    #     if bpy.context.scene.camera.name != "AC_Camera_3D":
    #         bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=preferences.camera_angle, scale=(1, 1, 1))
    #         bpy.context.scene.camera.name = "AC_Camera_3D"
    #     else:
    #         bpy.context.scene.camera.rotation_euler = preferences.camera_angle

    # setup camera
    if bpy.context.scene.camera is None:
        if camera_data:= bpy.data.cameras.get("AC_Camera_3D") is not None:
            if bpy.data.objects.get("AC_Camera_3D") is None: 
                camera_object = bpy.data.objects.new("AC_Camera_3D", camera_data)
            else:
                camera_object = bpy.data.objects.get("AC_Camera_3D")
            render_scene.collection.objects.link(camera_object)  
            camera = bpy.context.scene.objects.get("AC_Camera_3D")
            bpy.context.scene.camera = camera
        else:
            bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=preferences.camera_angle, scale=(1, 1, 1))
            bpy.context.scene.camera.name = "AC_Camera_3D"
    elif bpy.context.scene.camera.name != "AC_Camera_3D":
        if bpy.context.scene.objects.get("AC_Camera_3D") is None:
            if bpy.data.objects.get("AC_Camera_3D") is None: 
                if bpy.data.cameras.get("AC_Camera_3D") is None:
                    camera_data = bpy.data.cameras.new(name="AC_Camera_3D") 
                else:
                    camera_data = bpy.data.cameras["AC_Camera_3D"]
                camera_object = bpy.data.objects.new("AC_Camera_3D", camera_data)
            render_scene.collection.objects.link(camera_object)    
        camera = bpy.context.scene.objects.get("AC_Camera_3D")
        bpy.context.scene.camera = camera
    else:
        camera = bpy.context.scene.camera



    camera.location = 0,0,0
    camera.rotation_euler = preferences.camera_angle

    # sun = False
    # for ob in bpy.context.scene.objects:
    #     if ob.type == "LIGHT":
    #         sun = True

    # if not sun:
    #     bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 0), rotation=(0.785398, 0.785398, -1.5708), scale=(1, 1, 1))

    bpy.context.scene.render.resolution_y = preferences.preview_resolution
    bpy.context.scene.render.resolution_x = preferences.preview_resolution
    bpy.context.scene.render.use_freestyle = False

    if not bpy.context.scene.world:
        bpy.ops.world.new()
        bpy.context.scene.world = bpy.data.worlds[-1]

    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    bpy.context.scene.render.film_transparent = True


    # setup render
    filename = object_name + "_preview.png"
    filepath = save_path + "\\" + filename
    bpy.context.scene.render.filepath = filepath
    bpy.context.scene.render.engine = "CYCLES"
    object.select_set(True)
    bpy.ops.view3d.camera_to_view_selected()
    bpy.context.scene.camera.data.clip_start = 0.000001

    bpy.ops.render.render(write_still=True)

    render_scene.collection.objects.unlink(object)
    bpy.context.window.scene = current_scene

class ACACCF_OT_apply(bpy.types.Operator):
    bl_idname = "acaccf.apply"
    bl_label = "Apply object"
    bl_description = "Apply modifiers and join objects. Mendatory step for proper export."

    merge_by_distance: bpy.props.BoolProperty(default=True, name="merge by distance", description="Merge vertices by distance")
    delete_loose: bpy.props.BoolProperty(default=True, name="delete_loose", description="Delete loose geometry")

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        
        def apply_modifiers(obj):
            # ctx = bpy.context.copy()
            # ctx['object'] = obj
            with context.temp_override(object = obj):
                for _, m in enumerate(obj.modifiers):
                    try:
                        # with context.temp_override(modifier = m):
                        bpy.ops.object.modifier_apply(modifier= m.name)
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
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode='EDIT')
        if self.merge_by_distance:
            bpy.ops.mesh.remove_doubles()
        if self.delete_loose:
            bpy.ops.mesh.delete_loose(use_faces=True)
        bpy.ops.mesh.vert_connect_nonplanar(angle_limit=0.0174533)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ACACCF_OT_Proxy_remove_doubles(bpy.types.Operator):
    bl_idname = "acaccf.remove_doubles"
    bl_label = "remove doubles"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')
        return{"FINISHED"}
    
class ACACCF_OT_Proxy_delete_loose(bpy.types.Operator):
    bl_idname = "acaccf.delete_loose"
    bl_label = "delete loose"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete_loose()
        bpy.ops.object.mode_set(mode='OBJECT')
        return{"FINISHED"}
    
class ACACCF_OT_Proxy_connect_coplanar(bpy.types.Operator):
    bl_idname = "acaccf.connect_coplanar"
    bl_label = "connect coplanar"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.vert_connect_nonplanar(angle_limit=0.0174533)
        bpy.ops.object.mode_set(mode='OBJECT')
        return{"FINISHED"}
    

class ACACCF_OT_apply_modifiers(bpy.types.Operator):
    bl_idname = "acaccf.apply_modifiers"
    bl_label = "Apply modifiers"
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
        for obj in object_list:            
            apply_modifiers(obj)
        return {"FINISHED"}


class ACACCF_OT_export(bpy.types.Operator):
    bl_idname = "acaccf.export"
    bl_label = "export"

    def draw(self, context):
        prop = context.scene.acaccf
        layout = self.layout
        layout.prop(prop, "object_name")
        layout.prop(prop, "save_path")


        layout.prop(prop, "export_lod")
        layout.prop(prop, "lod_0", text="Detailed" if prop.export_lod else "Model")
        if prop.export_lod:
            layout.prop(prop, "lod_1")
        layout.separator(factor=1)

        layout.prop(prop, "smooth_angle")
        if not prop.export_lod:
            layout.prop(prop, "is_placable")

    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        start_time = time()

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
            bpy.context.scene.render.engine = 'CYCLES'
            obj = bpy.context.active_object
            symbol_script = mesh_to_symbol.run_script(props.save_path, start_obj=obj)

            # create 3d script
            mesh_script, Textures_ids, z_shift = mesh_to_gdl.run_script(props.smooth_angle, texture_folder, ob = obj)
            
            #get back to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Get the list of materials for AC override
            object_materials = []
            object_surfaces = []
            for material in lod.data.materials:
                if material:
                    if not utils.cleanString(material.name) in object_materials:
                        object_materials.append(utils.cleanString(material.name))
                        object_surfaces.append(f'sf_{utils.cleanString(material.name)}')
            if not len(object_materials) > 0:
                object_materials = ["material_default"]
                object_surfaces = ["sf_material_default"]


            create_thumbnail(lod, props.object_name, thumbnail_path)


            # complete xml
            xml = xml_template.get_xml(props.object_name, is_placable, symbol_script, mesh_script, size_x, size_y, size_z, z_shift, lod_number, Textures_ids, object_surfaces, object_materials, ac_version, thumbnail_path=thumbnail_path)
            # xml = xml_template.get_xml(props.object_name, is_placable, "PROJECT2{2} 3, -90, 51", mesh_script, size_x, size_y, size_z, z_shift, lod_number, Textures_ids, object_surfaces, object_materials, ac_version, thumbnail_path=thumbnail_path)


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


                convertion_result = subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart -img "{texture_folder}" "{props.save_path + props.object_name}_LOD{str(i)}.xml" "{props.save_path + props.object_name}_LOD{str(i)}.gsm"', stdout=subprocess.PIPE)
                #print(convertion_result.stdout.decode("utf-8"))
                i += 1
            create_thumbnail(props.lod_0, props.object_name, texture_folder)
            process_lod_xml(props, object_dimensions, object_surfaces, object_materials,  ac_version, thumbnail_path=texture_folder)
            convertion_result = subprocess.run(f'"{lp_xmlconverter_path}" xml2libpart -img "{texture_folder}" "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', stdout=subprocess.PIPE)
            #print(convertion_result.stdout.decode("utf-8"))
                #subprocess.call(f'"{lp_xmlconverter_path}" xml2libpart "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', shell=True)

        else:
            # Ensure at lease one object is being submitted to the process function
            lod = props.lod_0 if props.lod_0 else props.lod_1
            lod = context.active_object if not lod else lod
            process_object(props, lod, props.is_placable, thumbnail_path=texture_folder, lod_number=None )
            convertion_result= subprocess.run(f'"{lp_xmlconverter_path}" xml2libpart -img "{texture_folder}" "{props.save_path + props.object_name + ".xml"}" "{props.save_path + props.object_name}.gsm"', stdout=subprocess.PIPE)
            print(convertion_result.stdout.decode("utf-8"))

        end_time = time()
        print(f"elapsed_time = {end_time - start_time}")
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
        
        if props.object_name == "":
            # Set the blender's file name as object name. 
            props.object_name = bpy.path.basename(bpy.context.blend_data.filepath).replace(".blend", "")

        if props.save_path == "C:\\" or not props.save_path:
            # Set the blender's file name as object name. 
            props.save_path = os.path.dirname(bpy.context.blend_data.filepath) + "\\"
        
        properties.AC_PropertyGroup_props.ensure_default_props(context.scene.archicad_converter_props, context)
        return context.window_manager.invoke_props_dialog(self)
        
class AC_OT_property_add(bpy.types.Operator):
    bl_idname = "acaccf.property_add"
    bl_label = "add property"

    def execute(self, context):
        prop = context.scene.archicad_converter_props
        item = prop.collection.add()
        item.name = "property_" + str(len(prop.collection))
        item.identifier = "property_" + str(len(prop.collection))
        prop.active_user_index = len(prop.collection) - 1
        return {"FINISHED"}

class AC_OT_property_remove(bpy.types.Operator):
    bl_idname = "acaccf.property_remove"
    bl_label = "add property"

    @classmethod
    def poll(cls, context):
        prop = context.scene.archicad_converter_props
        if prop.active_user_index < len(prop.collection):
            if not prop.collection[prop.active_user_index].name in ["PenAttribute_1", "lineTypeAttribute_1", "fillAttribute_1"]:
                return True

    def execute(self, context):
        prop = context.scene.archicad_converter_props
        prop.collection.remove(prop.active_user_index)
        if prop.active_user_index >= len(prop.collection):
            prop.active_user_index -= 1
        else:
            # force the update of the prop. Needed as I rely on it to ensure some props are still here.
            prop.active_user_index = prop.active_user_index
        return {"FINISHED"}

class AC_OT_property_up(bpy.types.Operator):
    bl_idname = "acaccf.property_up"
    bl_label = "up property"

    @classmethod
    def poll(cls, context):
        prop = context.scene.archicad_converter_props
        return prop.active_user_index > 0

    def execute(self, context):
        prop = context.scene.archicad_converter_props

        prop.collection.move(prop.active_user_index, prop.active_user_index-1)
        prop.active_user_index -= 1
        return {"FINISHED"}

class AC_OT_property_down(bpy.types.Operator):
    bl_idname = "acaccf.property_down"
    bl_label = "down property"

    @classmethod
    def poll(cls, context):
        prop = context.scene.archicad_converter_props
        return prop.active_user_index < len(prop.collection) - 1
    
    def execute(self, context):
        prop = context.scene.archicad_converter_props
        prop.collection.move(prop.active_user_index, prop.active_user_index+1)
        prop.active_user_index += 1
        return {"FINISHED"} 


class ACCTEST_OT_dummy(bpy.types.Operator):
    bl_idname = "acaccf.dummy"
    bl_label = "dummy"

    def execute(self, context):
        from . import mesh_to_symbol

        mesh_to_symbol.run_script("C:\\tmp\\", bpy.context.active_object)
        return {"FINISHED"}

classes = [
    ACACCF_OT_export,
    ACCTEST_OT_dummy,
    ACACCF_OT_apply,
    AC_OT_property_add,
    AC_OT_property_remove,
    AC_OT_property_down,
    AC_OT_property_up,
    ACACCF_OT_apply_modifiers,
    ACACCF_OT_Proxy_remove_doubles,
    ACACCF_OT_Proxy_delete_loose,
    ACACCF_OT_Proxy_connect_coplanar
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
