import bpy
import addon_utils
import bmesh
from mathutils import Vector


preferences = bpy.context.preferences.addons[__package__].preferences
current_scene = bpy.context.scene
dissolve_angle = 10 * (3.1459/180)
merge_distance = 0.00075


    # https://blender.stackexchange.com/questions/254419/how-to-export-object-outline-as-dwg-or-svg-lines-without-modifying-mesh
    # https://www.youtube.com/watch?v=ji06I_KalEw
    # https://blender.stackexchange.com/questions/155275/how-to-set-freestyle-line-set-setting-using-python


def setup_scene(filepath, start_obj:bpy.types.Object):
    global preferences
    global current_scene

    if not bpy.data.scenes.get("AC_render_scene"):
        bpy.ops.scene.new(type='NEW')
        new_scene = bpy.data.scenes[-1]
        new_scene.name = "AC_render_scene"
    
    render_scene = bpy.data.scenes.get("AC_render_scene")
    bpy.context.window.scene = render_scene

    frame_number = str(bpy.data.scenes["AC_render_scene"].frame_current)
    frame_number = "0" * (4 - (len(frame_number))) + frame_number
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
    if freestyle_settings.linesets.active is None or freestyle_settings.linesets.active is not None and freestyle_settings.linesets.active.name != "AC_2d_lineset":
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
        
    # moves the camera over the real center of the object
    local_bbox_center = 0.125 * sum((Vector(b) for b in start_obj.bound_box), Vector())
    global_bbox_center = start_obj.matrix_world @ local_bbox_center


    # setup camera
    if bpy.context.scene.camera is None:
        bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(global_bbox_center[0],global_bbox_center[1],start_obj.dimensions[2] + 5), rotation=(0,0,0), scale=(1, 1, 1))
        bpy.context.scene.camera.name = "AC_Camera_2D"
    elif bpy.context.scene.camera.name != "AC_Camera_2D":
        if bpy.context.scene.objects.get("AC_Camera_2D") is None:
            if bpy.data.objects.get("AC_Camera_2D") is None: 
                if bpy.data.cameras.get("AC_Camera_2D") is None:
                    camera_data = bpy.data.cameras.new(name="AC_Camera_2D") 
                else:
                    camera_data = bpy.data.cameras["AC_Camera_2D"]
                camera_object = bpy.data.objects.new("AC_Camera_2D", camera_data)
            render_scene.collection.objects.link(camera_object)    
        camera = bpy.context.scene.objects.get("AC_Camera_2D")
        bpy.context.scene.camera = camera
    else:
        camera = bpy.context.scene.camera



    camera.location = global_bbox_center[0],global_bbox_center[1],start_obj.dimensions[2] + 5
    camera.rotation_euler = (0,0,0)
    camera.data.type = "ORTHO"

    return  render_scene, camera, frame_number


def create_mesh(render_scene, camera, frame_number, filepath, start_obj:bpy.types.Object):
    # import object and scale camera to dimensions
    render_scene.collection.objects.link(start_obj)
    obj_greatest_dim = max(start_obj.dimensions[0], start_obj.dimensions[1])
    camera.data.ortho_scale = obj_greatest_dim
    start_obj.select_set(True)
    
    # max_x = 0
    # max_x_vertex = None
    # max_x_vertex = None
    # max_y = 0
    # max_y_vertex = None
    # max_y_vertex = None
    # mesh = start_obj.data

    # Parcourt tous les vertices du mesh
#     for vertex in mesh.vertices:
#         # Convertit la position du vertex dans le système de coordonnées mondial
#         world_vertex = start_obj.matrix_world @ vertex.co
        
#         # Vérifie si le vertex est plus loin dans la direction -X
#         if world_vertex.x < max_x:
#             max_x = world_vertex.x
#             max_x_vertex = world_vertex
#             rel_x_vertex = vertex.co.x
#         if world_vertex.y > max_y:
#             max_y = world_vertex.y
#             max_y_vertex = world_vertex
#             rel_y_vertex = vertex.co.y

#     offset = max(abs(max_x_vertex[0])-abs(rel_x_vertex), abs(max_y_vertex[1])-abs(rel_y_vertex))
# #######
#
#
# Voir le calcul de l'offset. faut arriver à mettre le centre du mesh au millieu du monde.
#
#
########


    bpy.ops.render.render(use_viewport=True)

    

    render_scene.collection.objects.unlink(start_obj)

    svg_name = frame_number+".svg"

    bpy.ops.import_curve.svg(filepath = filepath+svg_name)
    svg_collection = bpy.context.scene.collection.children[svg_name]
    bpy.context.view_layer.objects.active = svg_collection.objects[-1]

    new_scale = max(start_obj.dimensions[:-1]) / 0.1445 

    symbol_script = ""

    for obj in bpy.context.scene.objects:
        obj.select_set(False)

    offset = max(abs(start_obj.bound_box[3][0]), abs(start_obj.bound_box[3][1]))

    # sorts lines and hatch (curves and meshes)
    for obj in svg_collection.objects:
        # obj.select_set(True)
        obj.scale = (new_scale, new_scale, new_scale)
        obj.location = (offset*-1, offset, 0)

        # Apply transform at low level to avoid operators
        mb = obj.matrix_basis
        if hasattr(obj.data, "transform"):
            obj.data.transform(mb)
        for c in obj.children:
            c.matrix_local = mb @ c.matrix_local
            
        obj.matrix_basis.identity()

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.mode_set(mode='EDIT')

        if len(obj.data.polygons):         
            symbol_script += mesh_to_hatch(obj)
        else:
            symbol_script += mesh_to_lines(obj)
    return symbol_script


def mesh_to_hatch(obj):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    bmesh.ops.dissolve_limit(bm, angle_limit=dissolve_angle, verts=bm.verts, edges=bm.edges)
    script_part = ""

    for face in bm.faces:
        max_n_loop = len(face.loops)
        command_string = f"POLY2_B {max_n_loop+1}, 2, fillfgpen_1, fillbgpen_1, \n"
        for loop in face.loops:
            command_string += f"{str('%.4f' % loop.vert.co[0])}, {str('%.4f' % loop.vert.co[1])}, 33,\n"
        # close polygon
        command_string += f"{str('%.4f' % face.loops[0].vert.co[0])}, {str('%.4f' % face.loops[0].vert.co[1])}, -1\n"
        script_part += command_string
    bm.free()
    return script_part


def mesh_to_lines(obj):
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_distance)
    bmesh.ops.dissolve_limit(bm, angle_limit=dissolve_angle, verts=bm.verts, edges=bm.edges)
    script_part = ""

    for edge in bm.edges:
        max_n_loop = len(edge.verts)
        command_string = f"POLY2 {max_n_loop}, 1,\n"
        for vert in edge.verts:
            command_string += f"{str('%.4f' % vert.co[0])}, {str('%.4f' % vert.co[1])},\n"
        # close polygon
        command_string = command_string[:-2] + "\n"
        script_part += command_string
    bm.free()
    return script_part


def run_script(filepath, start_obj:bpy.types.Object):
    curent_objects = bpy.context.scene.objects[:]
    render_scene, camera, frame_number = setup_scene(filepath, start_obj)
    symbol_script = create_mesh(render_scene, camera, frame_number, filepath, start_obj)

    for obj in bpy.context.scene.objects:
        if not obj.name in curent_objects:
            if obj.type == "MESH":
                bpy.data.objects.remove(obj)
    
    for col in bpy.context.scene.collection.children:
        bpy.data.collections.remove(col)

    bpy.context.window.scene = current_scene
    bpy.ops.object.mode_set(mode='EDIT')

    return symbol_script