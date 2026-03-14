import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

edge_status_layer_name = "original_edges"
# 0 = newly created
# 1 = original

# Build BVH to check vertex/face visibility of the mesh from the top view
def _build_object_bvh(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    world_matrix = obj.matrix_world.copy()
    for vert in bm.verts:
        vert.co = world_matrix @ vert.co

    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def _get_object_z_bounds(obj):
    world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    z_values = [corner.z for corner in world_corners]
    return min(z_values), max(z_values)


def _is_world_point_visible_on_object(bvh, point_world, ray_origin_z, epsilon=0.001):
    ray_origin = Vector((point_world.x, point_world.y, ray_origin_z))
    ray_direction = Vector((0.0, 0.0, -1.0))
    location, normal, index, distance = bvh.ray_cast(ray_origin, ray_direction)
    return location is not None and (location - point_world).length <= epsilon


def filter_faces_by_vertex_visibility(obj, depsgraph, scene, mesh_z_size):
    """Compute the visibility of top-view faces using only the target object.

    This avoids false negatives caused by other meshes present in the scene.
    """

    del depsgraph, scene  # Kept for compatibility with existing call sites.

    bvh = _build_object_bvh(obj)
    _, top_z = _get_object_z_bounds(obj)
    ray_origin_z = top_z + max(mesh_z_size, 0.001) + 0.1

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Mark original edges for easier cleanup later.
    edges_status_layer = bm.edges.layers.int.get(edge_status_layer_name)
    if edges_status_layer is None:
        edges_status_layer = bm.edges.layers.int.new(edge_status_layer_name)
    for edge in bm.edges:
        edge[edges_status_layer] = 1

    faces_to_delete = []
    bmesh.ops.triangulate(bm, faces=list(bm.faces))

    for face in bm.faces:
        face_visible = False
        for vert in face.verts:
            vert_world = obj.matrix_world @ vert.co
            if _is_world_point_visible_on_object(bvh, vert_world, ray_origin_z):
                face_visible = True
                break
        if not face_visible:
            faces_to_delete.append(face)

    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()

    return edges_status_layer


def assign_materials_to_object(obj):
    """Assign a material to the object in order to identify created faces easily."""
    material_name = "AC_Material"

    # Check if material already exists. Creates it otherwise.
    if material_name in bpy.data.materials:
        material = bpy.data.materials[material_name]
    else:
        material = bpy.data.materials.new(name=material_name)

    # Clear materials of the object to assign ours.
    obj.data.materials.clear()
    for _ in range(0, 2):
        obj.data.materials.append(material)

    return material


def pretreatment(obj):
    # Ensures all faces are selected, and intersect them
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.intersect(mode='SELECT', separate_mode="ALL", solver='EXACT')
    bpy.ops.object.mode_set(mode='OBJECT')


def intersect_faces(obj, z_size):
    # ensure edit mode and selection
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
    bpy.ops.mesh.select_all(action='SELECT')

    # Destructive work on a copy. is it still needed ?
    # Flattens the mesh and put it at ground level
    bpy.ops.mesh.duplicate()
    bpy.ops.transform.resize(value=(1, 1, 0))
    bpy.ops.transform.translate(value=(0, 0, z_size * -0.5))

    # Create attribute to differenciate new faces.
    bm = bmesh.from_edit_mesh(obj.data)
    new_edges_layer = bm.edges.layers.int.get("new_edges")
    if new_edges_layer is None:
        new_edges_layer = bm.edges.layers.int.new("new_edges")

    for edge in bm.edges:
        edge[new_edges_layer] = 1 if edge.select else 0

    bpy.ops.mesh.delete(type="ONLY_FACE")

    for edge in bm.edges:
        edge.select = bool(edge[new_edges_layer] == 1)

    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, z_size)})
    bpy.ops.mesh.select_linked()

    # Material index 1 = original visible body, 0 = helper/cutter body.
    for face in bm.faces:
        face.material_index = 1 if face.select else 0

    bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode="ALL", solver='EXACT')

    for edge in bm.edges:
        edge.select = True
    for face in bm.faces:
        if face.material_index == 0:
            for edge in face.edges:
                edge.select = False

    bpy.ops.mesh.delete(type='EDGE')
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')


def filter_faces_by_restrictive_visibility(obj, scene, depsgraph):
    del scene, depsgraph  # Visibility is evaluated against the target object only.

    bvh = _build_object_bvh(obj)
    _, top_z = _get_object_z_bounds(obj)
    ray_origin_z = top_z + max(obj.dimensions[2], 0.001) + 0.1

    def is_face_visible(face):
        face_center_world = obj.matrix_world @ face.calc_center_median()
        if _is_world_point_visible_on_object(bvh, face_center_world, ray_origin_z):
            return True

        for vert in face.verts:
            vert_world = obj.matrix_world @ vert.co
            mid_point_world = (vert_world + face_center_world) * 0.5
            if _is_world_point_visible_on_object(bvh, mid_point_world, ray_origin_z):
                return True
        return False

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))

    faces_to_delete = [face for face in bm.faces if not is_face_visible(face)]
    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()


def _edge_to_2d_tuple(edge, precision=6):
    v1, v2 = edge.verts
    p1 = (round(float(v1.co.x), precision), round(float(v1.co.y), precision))
    p2 = (round(float(v2.co.x), precision), round(float(v2.co.y), precision))
    return tuple(sorted((p1, p2)))


def _serialize_edges(edges):
    serialized = []
    seen = set()
    for edge in edges:
        if len(edge.verts) != 2:
            continue
        key = _edge_to_2d_tuple(edge)
        if key in seen:
            continue
        seen.add(key)
        v1, v2 = edge.verts
        serialized.append((float(v1.co.x), float(v1.co.y), float(v2.co.x), float(v2.co.y)))
    return serialized


def simplify_beautify_mesh(obj, distance_threshold=0.0001, coplanar_threshold=0.9999, angle_limit=5):
    """Flatten and simplify the mesh for an optimized top-view 2D symbol.

    The important fix here is that we no longer return dead BMesh edge references.
    We also preserve true visible linework and dissolve only non-drawable coplanar
    splits, so the final hatches stay complete without redundant overlaps.
    """

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance_threshold)

    layer = bm.edges.layers.int.get(edge_status_layer_name)

    # Work in the actual top-view space from this point on.
    for v in bm.verts:
        v.co.z = 0.0

    # Remove helper edges introduced during face cutting/intersections.
    if layer is not None:
        helper_edges = [e for e in bm.edges if e[layer] == 0]
        if helper_edges:
            bmesh.ops.dissolve_edges(bm, edges=helper_edges, use_verts=False)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance_threshold)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # Identify which edges should really stay visible in the symbol.
    non_draw_edges = []
    for edge in bm.edges:
        if len(edge.verts) != 2:
            continue
        if not edge.is_manifold or len(edge.link_faces) < 2:
            continue

        face1, face2 = edge.link_faces[:2]
        dot = face1.normal.dot(face2.normal)
        if dot >= coplanar_threshold:
            non_draw_edges.append(edge)

    # Merge coplanar regions so we do not export extra polygons.
    if non_draw_edges:
        bmesh.ops.dissolve_edges(bm, edges=non_draw_edges, use_verts=False)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance_threshold)
    bmesh.ops.dissolve_limit(
        bm,
        angle_limit=0.0001,
        verts=bm.verts,
        edges=bm.edges,
    )

    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    final_contour_edges = []
    final_inner_edges = []
    for edge in bm.edges:
        if len(edge.verts) != 2:
            continue
        if not edge.is_manifold or len(edge.link_faces) < 2:
            final_contour_edges.append(edge)
        elif len(edge.link_faces) == 2:
            face1, face2 = edge.link_faces[:2]
            if face1.normal.dot(face2.normal) < coplanar_threshold:
                final_inner_edges.append(edge)

    serialized_inner_edges = _serialize_edges(final_inner_edges)
    serialized_contour_edges = _serialize_edges(final_contour_edges)

    bm.to_mesh(mesh)
    mesh.update()
    bm.free()

    return serialized_inner_edges, serialized_contour_edges


def _fmt(value):
    return f"{float(value):.4f}"


def _edge_key_from_coords(x1, y1, x2, y2, precision=6):
    p1 = (round(float(x1), precision), round(float(y1), precision))
    p2 = (round(float(x2), precision), round(float(y2), precision))
    return tuple(sorted((p1, p2)))


def mesh_to_GDL(obj, inner_edges, contour_edges):
    """Convert the processed top-view mesh into a clean 2D GDL script.

    Faces from the cleaned mesh become POLY2_B hatches.
    Edge snapshots returned by simplify_beautify_mesh become LINE2 commands.
    """

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    script_parts = []

    # Export hatch polygons from the final simplified mesh.
    for face in bm.faces:
        if len(face.verts) < 3:
            continue

        loops = list(face.loops)
        command = [f"POLY2_B {len(loops) + 1}, 2, fillfgpen_1, fillbgpen_1,"]
        for loop in loops:
            command.append(f"{_fmt(loop.vert.co.x)}, {_fmt(loop.vert.co.y)}, 33,")
        command.append(f"{_fmt(loops[0].vert.co.x)}, {_fmt(loops[0].vert.co.y)}, -1")
        script_parts.append("\n".join(command))

    bm.free()

    # Export linework with deduplication.
    drawn_edges = set()
    for x1, y1, x2, y2 in contour_edges + inner_edges:
        key = _edge_key_from_coords(x1, y1, x2, y2)
        if key in drawn_edges:
            continue
        drawn_edges.add(key)
        script_parts.append(f"LINE2 {_fmt(x1)}, {_fmt(y1)}, {_fmt(x2)}, {_fmt(y2)}")

    return "\n".join(script_parts) + ("\n" if script_parts else "")


def run_script(start_obj: bpy.types.Object):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    view_layer = bpy.context.view_layer

    original_active = view_layer.objects.active
    original_selected = list(bpy.context.selected_objects)
    original_mode = start_obj.mode if hasattr(start_obj, "mode") else "OBJECT"

    temp_obj = start_obj.copy()
    temp_obj.data = start_obj.data.copy()
    temp_obj.name = f"{start_obj.name}_AC2D_TMP"
    scene.collection.objects.link(temp_obj)

    symbol_script = ""

    try:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        temp_obj.select_set(True)
        view_layer.objects.active = temp_obj

        mesh = temp_obj.data
        mesh.update()
        z_size = temp_obj.dimensions[2]

        with bpy.context.temp_override(active_object=temp_obj, object=temp_obj, selected_objects=[temp_obj], selected_editable_objects=[temp_obj]):
            if temp_obj.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            pretreatment(temp_obj)
            assign_materials_to_object(temp_obj)
            filter_faces_by_vertex_visibility(temp_obj, depsgraph, scene, z_size)
            intersect_faces(temp_obj, z_size)
            filter_faces_by_restrictive_visibility(temp_obj, scene, depsgraph)
            inner_edges, contour_edges = simplify_beautify_mesh(
                temp_obj,
                distance_threshold=0.001,
                coplanar_threshold=0.9999,
                angle_limit=90,
            )
            symbol_script = mesh_to_GDL(temp_obj, inner_edges, contour_edges)

    finally:
        try:
            if temp_obj and temp_obj.name in bpy.data.objects:
                if view_layer.objects.active == temp_obj and temp_obj.mode != 'OBJECT':
                    with bpy.context.temp_override(active_object=temp_obj, object=temp_obj, selected_objects=[temp_obj], selected_editable_objects=[temp_obj]):
                        bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

        temp_mesh = temp_obj.data if temp_obj else None
        if temp_obj and temp_obj.name in bpy.data.objects:
            bpy.data.objects.remove(temp_obj, do_unlink=True)
        if temp_mesh and temp_mesh.users == 0:
            bpy.data.meshes.remove(temp_mesh)

        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in original_selected:
            if obj and obj.name in bpy.data.objects:
                obj.select_set(True)

        if start_obj and start_obj.name in bpy.data.objects:
            start_obj.select_set(True)
            view_layer.objects.active = start_obj
            try:
                if original_mode == 'EDIT' and start_obj.mode != 'EDIT':
                    with bpy.context.temp_override(active_object=start_obj, object=start_obj, selected_objects=[start_obj], selected_editable_objects=[start_obj]):
                        bpy.ops.object.mode_set(mode='EDIT')
                elif original_mode != 'EDIT' and start_obj.mode != original_mode:
                    with bpy.context.temp_override(active_object=start_obj, object=start_obj, selected_objects=[start_obj], selected_editable_objects=[start_obj]):
                        bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass
        elif original_active and original_active.name in bpy.data.objects:
            view_layer.objects.active = original_active

    return symbol_script
