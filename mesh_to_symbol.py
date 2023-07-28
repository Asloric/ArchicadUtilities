import bpy


def run_script(filepath):
    frame_number = str(bpy.data.scenes["Scene"].frame_current)
    frame_number = "0" * (4 - (len(frame_number))) + frame_number
    dissolve_angle = 10 * (3.1459/180)
    merge_distance = 0.002
    initial_objects = list(bpy.context.view_layer.objects)


    try:
        bpy.ops.preferences.addon_enable(module="render_freestyle_svg")
        bpy.ops.preferences.addon_enable(module="io_export_dxf")
    except:
        pass

    bpy.data.scenes["Scene"].render.use_freestyle = True

    bpy.data.scenes["Scene"].svg_export.use_svg_export = True
    bpy.data.linestyles["LineStyle"].geometry_modifiers["Sampling"].sampling = 100



    bpy.data.scenes["Scene"].render.filepath = filepath

    bpy.ops.render.render(use_viewport=True)


    bpy.ops.import_curve.svg(filepath = filepath+frame_number+".svg")


    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
        if obj not in initial_objects:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

    bpy.ops.object.join()
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold = merge_distance)
    bpy.ops.mesh.dissolve_limited(angle_limit = dissolve_angle)
    bpy.ops.mesh.remove_doubles(threshold = merge_distance)
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=False, use_faces=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.export.dxf(filepath = filepath+frame_number+".dxf", onlySelected = True, mesh_as = "LINEs")

    return None