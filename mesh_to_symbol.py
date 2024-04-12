import bpy
import addon_utils


    # https://blender.stackexchange.com/questions/254419/how-to-export-object-outline-as-dwg-or-svg-lines-without-modifying-mesh
    # https://www.youtube.com/watch?v=ji06I_KalEw
    # https://blender.stackexchange.com/questions/155275/how-to-set-freestyle-line-set-setting-using-python


def run_script(filepath, start_obj:bpy.types.Object):
    preferences = bpy.context.preferences.addons[__package__].preferences
    current_scene = bpy.context.scene
    if not bpy.data.scenes.get("AC_render_scene"):
        bpy.ops.scene.new(type='NEW')
        new_scene = bpy.data.scenes[-1]
        new_scene.name = "AC_render_scene"
    
    render_scene = bpy.data.scenes.get("AC_render_scene")
    bpy.context.window.scene = render_scene

    frame_number = str(bpy.data.scenes["AC_render_scene"].frame_current)
    frame_number = "0" * (4 - (len(frame_number))) + frame_number
    dissolve_angle = 10 * (3.1459/180)
    merge_distance = 0.00075
    initial_objects = list(bpy.context.view_layer.objects)



    is_enabled, is_loaded = addon_utils.check("render_freestyle_svg")
    if not is_loaded:
        print("Error : render_freestyle_svg addon is missing")
        return None # Fallback to default 2D Script
    
    if not is_enabled:
        addon_utils.enable("render_freestyle_svg")


    # setup scene freestyle settings to get contours
    bpy.data.scenes["AC_render_scene"].render.filepath = filepath
    bpy.data.scenes["AC_render_scene"].render.resolution_x = 512
    bpy.data.scenes["AC_render_scene"].render.resolution_y = 512
    bpy.data.scenes["AC_render_scene"].render.use_freestyle = True
    bpy.data.scenes["AC_render_scene"].svg_export.use_svg_export = True
    bpy.data.scenes["AC_render_scene"].svg_export.mode = "FRAME"
    bpy.data.scenes["AC_render_scene"].svg_export.object_fill = True
    bpy.context.window.view_layer.use_freestyle = True
    freestyle_settings = bpy.context.window.view_layer.freestyle_settings
    lineset = freestyle_settings.linesets.new("AC_2d_lineset")
    lineset.linestyle.use_export_fills = True
    lineset.select_silhouette = True
    lineset.select_crease = False
    lineset.select_border = False
    lineset.select_edge_mark = False
    lineset.select_contour = False
    lineset.select_external_contour = False
    lineset.select_material_boundary = False
    lineset.select_suggestive_contour = False
    lineset.select_ridge_valley = False





    # setup camera
    if bpy.context.scene.camera is None or bpy.context.scene.camera.name != "AC_Camera_2D":
        if bpy.context.scene.objects.get("AC_Camera_2D") is None:
            if bpy.data.objects.get("AC_Camera_2D") is None: 
                if bpy.data.cameras.get("AC_Camera_2D") is None:
                    camera_data = bpy.data.cameras.new(name="AC_Camera_2D") 
                camera_object = bpy.data.objects.new("AC_Camera_2D", camera_data)
            render_scene.collection.objects.link(camera_object)    
        camera = bpy.context.scene.objects.get("AC_Camera_2D")
        bpy.context.scene.camera = camera

    camera.location = 0,0,10
    camera.rotation_euler = (0,0,0)
    camera.data.type = "ORTHO"
    



    # import object and scale camera to dimensions
    render_scene.collection.objects.link(start_obj)
    obj_greatest_dim = max(start_obj.dimensions[0], start_obj.dimensions[1])
    camera.data.ortho_scale = obj_greatest_dim
    start_obj.select_set(True)

    max_x = 0
    max_x_vertex = None
    max_y = 0
    max_y_vertex = None
    mesh = start_obj.data

    # Parcourt tous les vertices du mesh
    for vertex in mesh.vertices:
        # Convertit la position du vertex dans le système de coordonnées mondial
        world_vertex = start_obj.matrix_world @ vertex.co
        
        # Vérifie si le vertex est plus loin dans la direction -X
        if world_vertex.x < max_x:
            max_x = world_vertex.x
            max_x_vertex = world_vertex
        if world_vertex.y > max_y:
            max_y = world_vertex.y
            max_y_vertex = world_vertex

    offset = max(abs(max_x_vertex[0]), abs(max_y_vertex[1]))



    bpy.ops.render.render(use_viewport=True)

    

    render_scene.collection.objects.unlink(start_obj)

    svg_name = frame_number+".svg"

    bpy.ops.import_curve.svg(filepath = filepath+svg_name)
    svg_collection = bpy.context.scene.collection.children[svg_name]
    bpy.context.view_layer.objects.active = svg_collection.objects[-1]

    new_scale = max(start_obj.dimensions) / 0.1445 

    # sorts lines and hatch (curves and meshes)
    hatch_objects = []
    line_objects = []
    for obj in svg_collection.objects:
        obj.select_set(True)
        obj.scale = (new_scale, new_scale, new_scale)
        obj.location = (offset*-1, offset, 0)
        if obj.type != "MESH":
            with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
                bpy.ops.object.convert(target="MESH")
                bpy.ops.object.transform_apply(location=True, scale=True)
                line_objects.append(obj)
        else:
            bpy.ops.object.transform_apply(location=True, scale=True)
            hatch_objects.append(obj)


    # Treat curves
    if len(line_objects):
        with bpy.context.temp_override(active_object=line_objects[-1], selected_objects=line_objects):   
            bpy.ops.object.join()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold = merge_distance)
            bpy.ops.object.mode_set(mode='OBJECT')
            
    
    # Treat surfaces
    if len(hatch_objects):
        with bpy.context.temp_override(active_object=hatch_objects[-1], selected_objects=hatch_objects):    
            bpy.ops.object.join() 
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.dissolve_limited(angle_limit = dissolve_angle)
            bpy.ops.object.mode_set(mode='OBJECT')

    # with bpy.context.temp_override(active_object=svg_collection.objects[-1], selected_objects=svg_collection.objects):
    #     bpy.ops.object.join()
    #     bpy.context.view_layer.objects.active = svg_collection.objects[-1]
    #     bpy.ops.object.mode_set(mode='EDIT')
    #     bpy.ops.mesh.select_all(action='SELECT')
    #     bpy.ops.mesh.remove_doubles(threshold = merge_distance)
    #     bpy.ops.mesh.dissolve_limited(angle_limit = dissolve_angle)
    #     bpy.ops.mesh.remove_doubles(threshold = merge_distance)
    #     bpy.ops.mesh.delete_loose(use_verts=True, use_edges=False, use_faces=False)
    #     bpy.ops.object.mode_set(mode='OBJECT')

    # bpy.ops.export.dxf(filepath = filepath+frame_number+".dxf", onlySelected = True, mesh_as = "LINEs")
    
    
    bpy.context.window.scene = current_scene
    bpy.ops.object.mode_set(mode='EDIT')


    return None