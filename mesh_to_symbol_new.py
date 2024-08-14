import bpy
import bmesh
from mathutils import Vector

def filter_faces_by_vertex_visibility(mesh, depsgraph, scene, mesh_z_size):
    """Compute the visibility of a face on top-view relying on the vertex visibility.
    If at least one vertex is visible, the face is considered visible. 
    """

    # check vertex visibility using raycasting
    def is_vertex_visible(vertex_co):
        ray_origin = vertex_co + Vector((0, 0, mesh_z_size+0.1))  # Start the ray above the mesh
        ray_direction = Vector((0, 0, -1))  # Cast the ray downward
        result, location, normal, index, obj, matrix = scene.ray_cast(depsgraph, ray_origin, ray_direction)
        return result and (location - vertex_co).length < 0.001
    
    bm = bmesh.new()
    bm.from_mesh(mesh)

    visible_faces = []
    bmesh.ops.triangulate(bm, faces=bm.faces)

    for face in bm.faces:
        face_visible = True
        for vert in face.verts:
            if is_vertex_visible(vert.co):
                face_visible = False
                break
        if face_visible is True:
            visible_faces.append(face)

    bmesh.ops.delete(bm, geom=visible_faces, context='FACES')

    bm.to_mesh(mesh)
    bm.free()

    return


def assign_materials_to_object(obj):
    """Assign a material to the object in order to identify easily the created faces from the cut plane"""
    
    material_name = "AC_Material"

    # Vérifier si le matériau existe déjà
    if material_name in bpy.data.materials:
        return bpy.data.materials[material_name]
    
    # Créer le matériau s'il n'existe pas
    material = bpy.data.materials.new(name=material_name)

    obj.data.materials.clear()  # Effacer les matériaux existants
    # Assigner les matériaux à l'objet
    for i in range(0, 2):
        obj.data.materials.append(material)


def intersect_faces(obj, z_size):
  
    with bpy.context.temp_override(active_object = obj, selected_objects = {obj}):

        # Passer en mode édition
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        # Sélectionner tout
        bpy.ops.mesh.select_all(action='SELECT')
         
        # Dupliquer tout
        bpy.ops.mesh.duplicate()

        # Applatir en Z (scale Z = 0)
        bpy.ops.transform.resize(value=(1, 1, 0))


        # Décale en Z pour que ça aille au plus bas du maillage original
        bpy.ops.transform.translate(value=(0, 0, z_size*-0.5))

        # Créer un attribut personnalisé pour les nouvelles faces
        bm = bmesh.new()
        bm = bmesh.from_edit_mesh(obj.data)
        new_edges_layer = bm.edges.layers.int.new("new_edges")
        for edge in bm.edges : 
            if edge.select:
                edge[new_edges_layer] = 1
            else:
                edge[new_edges_layer] = 0
        

    
            
        bpy.ops.mesh.delete(type="ONLY_FACE")


        # Sélectionner toutes les faces marquées précédemment
        for edge in bm.edges:
            if edge[new_edges_layer] == 1:
                edge.select = True
            else:
                edge.select = False
        

        # Extrude vers le haut de la hauteur du maillage original
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, z_size)})
        
        bpy.ops.mesh.select_linked()

        for face in bm.faces:
            if face.select:
                face.material_index = 2
            else:
                face.material_index = 1
            
            
        # Utiliser la commande bpy.ops.mesh.intersect(mode='SELECT', separate_mode="ALL")
        bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode="ALL", solver='EXACT')
        
        # Sélectionner toutes les faces marquées précédemment
        for edge in bm.edges:
            edge.select = True
        for face in bm.faces:
            if face.material_index == 1:
                for edge in face.edges:
                    edge.select = False
        
        bpy.ops.mesh.delete(type='EDGE')

        
        # Mettre à jour la mesh avec les sélections
        # bm.select_flush(True)
        bmesh.update_edit_mesh(obj.data)
        bm.free()
        
        # Repasser en mode objet pour terminer
        bpy.ops.object.mode_set(mode='OBJECT')

        return bm


def filter_faces_by_restrictive_visibility(obj, scene, depsgraph):

    # Définir une fonction pour vérifier la visibilité d'une face en utilisant le raycasting
    def is_face_visible(face):
        face_center = obj.matrix_world @ face.calc_center_median()
        ray_origin = face_center + Vector((0, 0, 10))  # Lancer le rayon 10 unités au-dessus du centre de la face
        ray_direction = Vector((0, 0, -1))  # Rayon vers le bas
        result, location, normal, index, hit_obj, matrix = scene.ray_cast(depsgraph, ray_origin, ray_direction)
        face.material_index = 1
        if index == face.index:
            face.material_index = 1
            return True
        else:
            # Si le rayon ne touche pas la face, vérifier la visibilité de tous les sommets
            for vert in face.verts:
                # Calculer la position à mi-chemin entre le sommet et le centre de la face
                mid_point = (obj.matrix_world @ vert.co + face_center) / 2
                vert_origin = mid_point + Vector((0, 0, 10))  # Lancer le rayon 10 unités au-dessus du point médian
                vert_result, vert_location, vert_normal, vert_index, vert_hit_obj, vert_matrix = scene.ray_cast(depsgraph, vert_origin, Vector((0, 0, -1)))
                if vert_location[2] - mid_point[2] < 0.001:
                    face.material_index = 1
                    return True
                else:
                    face.material_index = 2
                    # DEBUG: Add an edge to visualize the ray
                    #v1 = bm.verts.new(vert_origin)  # Coordonnées du premier vertex
                    #v2 = bm.verts.new(mid_point)  # Coordonnées du second vertex
                    #bm.edges.new((v1, v2))

                    return False
            return True

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Filtrer les faces visibles
    faces_to_keep = [face for face in bm.faces if not is_face_visible(face)]

    # Supprimer toutes les faces du maillage
    bmesh.ops.delete(bm, geom=faces_to_keep, context='FACES')

    bm.to_mesh(obj.data)
    bm.free()


def simplify_beautify_mesh(obj):

    # Merge by distance to fuse everything
    # Limited dissolve with low treshold to clean the cut lines

    # Loop through each face.
    # For each edge of the face
    # detect if it's a cliff or if it's connected.
    # if cliff, show it
    # if connected, hide it. (store it in a list)
    # For each vertice, check if coordinates are already in the list. 
    # If both are, edge is connected. mark them for dissolve.

    # set all vertices coordinates Z to 0.

    import bpy
    import bmesh
    from mathutils import Vector

    def merge_and_clean_mesh(obj, distance_threshold=0.001, coplanar_threshold=0.01):
        # Créer un BMesh à partir du mesh de l'objet
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Fusionner les sommets proches
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance_threshold)

        # Limiter la dissolution avec une faible tolérance pour nettoyer les lignes de coupe
        bmesh.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts)

        # Ensemble pour stocker les arêtes à dissoudre et celles à marquer comme "cliff"
        edges_to_dissolve = set()
        cliff_edges = set()

        # Dictionnaire pour stocker les coordonnées des sommets (arrondies pour comparaison)
        vertex_coords_dict = {}

        # Parcourir chaque face du maillage
        for face in bm.faces:
            for edge in face.edges:
                if len(edge.link_faces) == 2:
                    face1, face2 = edge.link_faces
                    # Vérifie si les deux faces sont coplanaires
                    if face1.normal.dot(face2.normal) > coplanar_threshold:
                        # Marquer les arêtes connectées pour dissolution
                        edges_to_dissolve.add(edge)
                    else:
                        # Marquer les arêtes comme des "cliffs"
                        cliff_edges.add(edge)
                else:
                    # Marquer comme "cliff" si l'arête n'est connectée qu'à une face
                    cliff_edges.add(edge)

                # Ajouter les coordonnées des sommets dans le dictionnaire
                for vert in edge.verts:
                    rounded_coords = tuple(round(c, 6) for c in vert.co)
                    if rounded_coords in vertex_coords_dict:
                        vertex_coords_dict[rounded_coords].append(vert)
                    else:
                        vertex_coords_dict[rounded_coords] = [vert]

        # Vérifier si des sommets partagent les mêmes coordonnées (en Z) pour identifier les arêtes connectées
        for coords, verts in vertex_coords_dict.items():
            if len(verts) > 1:
                for edge in bm.edges:
                    if edge.verts[0] in verts and edge.verts[1] in verts:
                        if edge not in cliff_edges:
                            edges_to_dissolve.add(edge)

        # Dissoudre les arêtes connectées
        if edges_to_dissolve:
            bmesh.ops.dissolve_edges(bm, edges=list(edges_to_dissolve), use_verts=False)

        # Aplatir toutes les coordonnées des sommets en Z à 0
        for vert in bm.verts:
            vert.co.z = 0

        # Mettre à jour le mesh avec les modifications
        bm.to_mesh(mesh)
        mesh.update()

        # Libérer le BMesh
        bm.free()

    # Appliquer la fonction à l'objet sélectionné
    obj = bpy.context.active_object
    merge_and_clean_mesh(obj)



    return

def run_script(start_obj:bpy.types.Object):
    # Get the mesh data
    # Ensure the mesh is up-to-date
    # Create a BMesh representation

    # Prepare the scene for raycasting
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # CAUTION ---------------------
    # MAKE SURE THERE IS NO OTHER OBJECT IN THE SCENE AS IT CAN OCCLUDE THE TARGET AND AFFECT RESULTS
    # CAUTION ---------------------


    mesh = start_obj.data
    mesh.update()


    z_size = start_obj.dimensions[2]
     
    with bpy.context.temp_override(active_object = start_obj, selected_objects = {start_obj}):
        # Assigner les matériaux à l'objet spécifié
        assign_materials_to_object(start_obj)
        
        filter_faces_by_vertex_visibility(mesh, depsgraph, scene, z_size)
        
        intersect_faces(start_obj, z_size)

        filter_faces_by_restrictive_visibility(start_obj, scene, depsgraph)

    # bpy.ops.object.mode_set(mode='OBJECT')
    mesh.update()
    # bm.free()
    
