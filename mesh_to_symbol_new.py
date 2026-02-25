import bpy
import bmesh
from mathutils import Vector

# mesh_to_symbol_new.py - 2D symbol generator using top-view raycasting.
#
# Workflow overview:
#   1. filter_faces_by_vertex_visibility: Remove faces fully hidden under other geometry (permissive pass).
#   2. intersect_faces: Create vertical cut planes projected from the mesh outline, then intersect
#      them with the original to resolve partial occlusion at silhouette edges.
#   3. filter_faces_by_restrictive_visibility: Remove any face that is not cleanly visible from above.
#   4. simplify_beautify_mesh: Flatten to Z=0 and dissolve redundant edges.
#
# IMPORTANT: run_script() currently modifies the mesh in-place but does NOT return a GDL string.
# The 2D symbol generation is work-in-progress; operators.py falls back to "PROJECT2 0, 1"
# (orthographic top projection) when symbol_script is None.

def filter_faces_by_vertex_visibility(mesh, depsgraph, scene, mesh_z_size):
    """Permissive top-view visibility filter.
    A face is KEPT if at least one of its vertices has unobstructed line-of-sight upward.
    Faces where NO vertex is visible (fully occluded) are removed.

    NOTE: The variable `visible_faces` is misleadingly named - it actually collects
    OCCLUDED faces (no vertex visible) which are then deleted. Should be `occluded_faces`.
    """

    # is_vertex_visible: cast a ray downward from above the vertex.
    # Returns True if the ray hits within 0.001m of the vertex itself (nothing blocking above it).
    def is_vertex_visible(vertex_co):
        ray_origin = vertex_co + Vector((0, 0, mesh_z_size+0.1))  # Start the ray above the mesh
        ray_direction = Vector((0, 0, -1))  # Cast the ray downward
        result, location, normal, index, obj, matrix = scene.ray_cast(depsgraph, ray_origin, ray_direction)
        return result and (location - vertex_co).length < 0.001

    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Triangulate first so visibility can be checked per-triangle (simpler geometry).
    occluded_faces = []  # NOTE: named "visible_faces" in original code - misleading.
    bmesh.ops.triangulate(bm, faces=bm.faces)

    for face in bm.faces:
        face_visible = True  # True here means "no vertex was found visible" (inverted flag).
        for vert in face.verts:
            if is_vertex_visible(vert.co):
                face_visible = False  # At least one vertex visible → face should be kept.
                break
        if face_visible is True:
            occluded_faces.append(face)  # No vertex visible → face is hidden → delete it.

    bmesh.ops.delete(bm, geom=occluded_faces, context='FACES')

    bm.to_mesh(mesh)
    bm.free()

    return


def assign_materials_to_object(obj):
    """Assign marker materials so that faces created by intersect_faces() can be identified later.

    intersect_faces() tags new cutting-plane faces with material_index=2 and original faces
    with material_index=1. filter_faces_by_restrictive_visibility() then uses material_index
    to distinguish them.

    CAUTION: This CLEARS the object's existing materials. The original materials are lost.
    This is intentional (the duplicate being processed doesn't need materials for the 2D symbol),
    but it means this function must only be called on a disposable copy.
    """
    material_name = "AC_Material"

    if material_name in bpy.data.materials:
        return bpy.data.materials[material_name]

    material = bpy.data.materials.new(name=material_name)

    obj.data.materials.clear()  # Destroy existing material slots.
    # Add the same material twice so material_index 0 and 1 both exist (used as slot 1 and 2 in intersect_faces).
    for i in range(0, 2):
        obj.data.materials.append(material)


def intersect_faces(obj, z_size):
    """Create vertical cutting planes from the mesh's projected outline, then intersect
    them with the original mesh to resolve partial occlusion at silhouette boundaries.

    The algorithm:
    1. Duplicate all edges and flatten them to Z = z_size * -0.5 (below the mesh).
    2. Mark duplicated edges with a custom "new_edges" layer attribute.
    3. Delete the faces of the flat copy (keep only edges as a 2D outline).
    4. Extrude the flat outline edges vertically by z_size (creating vertical wall planes).
    5. Mark vertical walls as material_index=2, original geometry as material_index=1.
    6. Intersect the walls (SELECT) against the original mesh (UNSELECT) to get cut lines
       exactly where the silhouette edges project onto the underlying faces.
    7. Remove the vertical wall edges (material_index != 1) leaving only the intersection cuts.

    The result is the original mesh with additional edges along its silhouette projection,
    enabling filter_faces_by_restrictive_visibility to cleanly split partially-occluded faces.
    """
    with bpy.context.temp_override(active_object = obj, selected_objects = {obj}):

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.mesh.select_all(action='SELECT')

        # Step 1: Duplicate all edges and flatten to a 2D outline at the bottom of the bounding box.
        bpy.ops.mesh.duplicate()
        bpy.ops.transform.resize(value=(1, 1, 0))            # Scale Z → 0 (flatten)
        bpy.ops.transform.translate(value=(0, 0, z_size*-0.5))  # Move down below the mesh

        # Step 2: Tag the newly duplicated edges in a custom bmesh layer for later selection.
        bm = bmesh.new()
        bm = bmesh.from_edit_mesh(obj.data)
        new_edges_layer = bm.edges.layers.int.new("new_edges")
        for edge in bm.edges:
            if edge.select:
                edge[new_edges_layer] = 1  # Duplicated edges (the flat outline)
            else:
                edge[new_edges_layer] = 0  # Original edges



        # Step 3: Remove the face geometry of the flat copy (keep only the outline edges).
        bpy.ops.mesh.delete(type="ONLY_FACE")

        # Re-select only the flat outline edges using the layer tag.
        for edge in bm.edges:
            if edge[new_edges_layer] == 1:
                edge.select = True
            else:
                edge.select = False

        # Step 4: Extrude the flat outline edges upward by z_size to create vertical wall planes.
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, z_size)})

        # Step 5: Select everything linked to the extruded walls; tag faces by material index.
        bpy.ops.mesh.select_linked()
        for face in bm.faces:
            if face.select:
                face.material_index = 2  # Cutting plane faces (walls)
            else:
                face.material_index = 1  # Original mesh faces

        # Step 6: Boolean intersect: walls (SELECT) cut the original mesh (UNSELECT).
        # This adds new edges along the intersection lines on the original mesh faces.
        bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode="ALL", solver='EXACT')

        # Step 7: Remove the vertical wall edges; keep only the intersection cut edges on the original.
        for edge in bm.edges:
            edge.select = True
        for face in bm.faces:
            if face.material_index == 1:  # Original mesh faces: deselect their edges (keep them).
                for edge in face.edges:
                    edge.select = False

        bpy.ops.mesh.delete(type='EDGE')  # Delete remaining selected edges (wall geometry).

        bmesh.update_edit_mesh(obj.data)
        bm.free()

        bpy.ops.object.mode_set(mode='OBJECT')

        return bm  # NOTE: bm is freed above; this returns an invalid bmesh reference.


def filter_faces_by_restrictive_visibility(obj, scene, depsgraph):
    """Restrictive top-view visibility filter (called after intersect_faces).
    A face is KEPT only if it is fully visible from above.
    If the face center OR any midpoint between a vertex and the center is occluded, the face is removed.

    NOTE: `faces_to_keep` is misleadingly named - it actually collects faces to DELETE
    (those where is_face_visible returns False). Should be `faces_to_remove`.
    """

    def is_face_visible(face):
        """Returns True if the face is cleanly visible from above (nothing occluding it)."""
        face_center = obj.matrix_world @ face.calc_center_median()
        ray_origin = face_center + Vector((0, 0, 10))
        ray_direction = Vector((0, 0, -1))
        result, location, normal, index, hit_obj, matrix = scene.ray_cast(depsgraph, ray_origin, ray_direction)
        face.material_index = 1
        if index == face.index:
            # Ray hits this exact face → face center is directly visible.
            face.material_index = 1
            return True
        else:
            # Face center not directly hit (occluded or at a seam).
            # Fall back to checking midpoints between each vertex and the face center.
            for vert in face.verts:
                mid_point = (obj.matrix_world @ vert.co + face_center) / 2
                vert_origin = mid_point + Vector((0, 0, 10))
                vert_result, vert_location, vert_normal, vert_index, vert_hit_obj, vert_matrix = scene.ray_cast(depsgraph, vert_origin, Vector((0, 0, -1)))
                if vert_location[2] - mid_point[2] < 0.001:
                    # Midpoint hit height is nearly the same as the midpoint → visible.
                    face.material_index = 1
                    return True
                else:
                    # Hit something higher → occluded.
                    face.material_index = 2
                    # DEBUG: Commented-out edge visualization:
                    #v1 = bm.verts.new(vert_origin)
                    #v2 = bm.verts.new(mid_point)
                    #bm.edges.new((v1, v2))
                    return False
            return True  # All vertex checks passed → visible.

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # NOTE: `faces_to_keep` is faces where is_face_visible=False (NOT visible) → these are deleted.
    faces_to_remove = [face for face in bm.faces if not is_face_visible(face)]

    bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES')

    bm.to_mesh(obj.data)
    bm.free()


def simplify_beautify_mesh(obj, distance_threshold=0.001):
    """Flatten mesh to Z=0 and dissolve redundant edges created by intersection cuts.

    The intersection step often leaves many small co-linear edges along cut lines.
    dissolve_limit removes edges/verts where the angle between adjacent edges/faces
    is below the limit (2 degrees here), effectively merging collinear segments.
    It is called multiple times because each pass can expose new collinear edges
    that were hidden by previously-dissolved geometry.
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance_threshold)

    # Dissolve vertices where angle between adjacent edges is < 2° (collinear - from intersection artifacts).
    bmesh.ops.dissolve_limit(bm, angle_limit=2, verts=bm.verts)

    # Flatten all vertices to Z=0 for a clean 2D plan symbol.
    for v in bm.verts:
        v.co.z = 0

    # Repeated dissolve passes to converge on minimal edge count.
    # Each pass may uncover new collinear edges after the previous one merged vertices.
    bmesh.ops.dissolve_limit(bm, angle_limit=2, edges=bm.edges)
    bmesh.ops.dissolve_limit(bm, angle_limit=2, edges=bm.edges)
    bmesh.ops.dissolve_limit(bm, angle_limit=2, edges=bm.edges)
    bmesh.ops.dissolve_limit(bm, angle_limit=2, edges=bm.edges)

    bm.to_mesh(mesh)
    mesh.update()
    bm.free()

    return


def run_script(start_obj:bpy.types.Object):
    """Run the full 2D symbol extraction pipeline on start_obj.

    IMPORTANT: This function operates on the object in-place (destructive).
    It should be called on a DUPLICATE, not the original.

    CAUTION: Scene must contain ONLY the target object during raycasting.
    Any other visible geometry will occlude the raycasts and corrupt visibility results.

    BUG (callers): operators.py calls this as:
        run_script(props.save_path, start_obj=obj)
    But the signature is run_script(start_obj). The extra positional argument will cause a TypeError.

    NOTE: This function currently returns None. The GDL output stage is not yet implemented.
    operators.py uses the return value as symbol_script; xml_template.py falls back to
    "PROJECT2 0, 1" (orthographic top projection) when symbol_script is None.
    """

    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    mesh = start_obj.data
    mesh.update()

    z_size = start_obj.dimensions[2]

    with bpy.context.temp_override(active_object = start_obj, selected_objects = {start_obj}):
        # Step 1: Clear materials and add marker material for face tagging.
        assign_materials_to_object(start_obj)
        # Step 2: Permissive filter - remove faces with no visible vertex (fully occluded).
        filter_faces_by_vertex_visibility(mesh, depsgraph, scene, z_size)
        # Step 3: Create vertical intersection cuts to split partially-occluded faces.
        intersect_faces(start_obj, z_size)
        # Step 4: Restrictive filter - remove faces not cleanly visible after intersection.
        filter_faces_by_restrictive_visibility(start_obj, scene, depsgraph)
        # Step 5: Flatten to Z=0 and clean up collinear edges.
        simplify_beautify_mesh(start_obj, distance_threshold=0.001)

    # TODO: Convert the remaining visible faces into GDL POLY2_B commands and return the script string.

    
