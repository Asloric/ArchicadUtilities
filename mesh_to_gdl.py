import bpy
import bmesh
from math import *
from . import utils

# GDL data structures:
# TEVE = Texture Vertex: position (X,Y,Z) + UV texture coordinates (U,V)
# EDGE = connects two TEVEs, knows its two adjacent faces (f1, f2) and smoothness
# PGON = polygon, references a list of EDGEs
# Together these form the "body" section of a GDL 3D script.

# CAUTION: TEVE and EDGE use class-level lists as shared state (module-level singleton pattern).
# They MUST be explicitly cleared via TEVE.clear() / EDGE.clear() between export calls.
# Not thread-safe; only one export can run at a time.
class TEVE():
    instances = []
    rinstances = []  # Reverse-ordered list for faster tail-lookups (not actually used for lookup - dict is used instead)
    coords_dict = {} # O(1) dedup: key=(x,y,z,u,v) → TEVE instance. Avoids duplicate vertices.
    min_z = 0.0  # Tracks the lowest Z coordinate; used to compute z_shift so origin is at floor level.

    def __init__(self, x,y,z,u,v, index) -> None:
        self.index = index
        self.x = x
        self.y = y
        self.z = z
        self.u = u
        self.v = v
        float_z = float(z)
        if float_z < TEVE.min_z:
            TEVE.min_z = float_z

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.rinstances = []
        cls.coords_dict = {}
        cls.min_z = 0

    @classmethod
    def new_teve(cls, x,y,z,u,v, index):
        self = cls(x,y,z,u,v, index)
        is_present = self.is_present(self)
        if not is_present:
            cls.coords_dict[(x,y,z,u,v)] = self
            cls.instances.append(self)
            cls.rinstances.insert(0, self)
            # Overwrite the index set in __init__ with the actual position in the list (0-based).
            setattr(self, "index", cls.instances.index(self))
            return self
        else: return is_present  # Return the existing TEVE so faces share the same vertex reference.

    @classmethod
    def get_output(cls):
        # Produces GDL TEVE lines. The `!index` comment is a debug aid (GDL ignores comments).
        list = []
        for teve in cls.instances:
            list.append(f"TEVE {teve.x}, {teve.y}, {teve.z}, {teve.u}, {teve.v}   !{teve.index}")
        return list

    @classmethod
    def is_present(cls, self):
        return cls.coords_dict.get((self.x, self.y, self.z, self.u, self.v))


# EDGE represents a directed edge in GDL topology.
# GDL allows at most 2 faces per edge (manifold mesh requirement).
# When the same Blender edge is shared by two faces with opposite winding,
# one is stored as a "mirror" with a negative index - this is GDL convention
# for reversed edge orientation in a polygon definition.
class EDGE():
    instances = []
    rinstances = []
    bl_instances = {}  # Maps Blender edge object → list of GDL EDGE instances derived from it.

    def __init__(self, v1, v2, smooth, bl_index, bl_edge):
        self.bl_edge = bl_edge
        self.bl_index = bl_index
        self.f1 = -1  # First adjacent face ID (-1 = unset)
        self.f2 = -1  # Second adjacent face ID (-1 = unset)
        self.v1 = v1
        self.v2 = v2
        self.smooth = smooth

    def add_face(self, face_id):
        if self.f1 == -1:
            self.f1 = face_id
        elif self.f2 == -1:
            self.f2 = face_id
        else:
            print("ERROR: MORE THAN 2 FACES FOR THIS EDGE", self.bl_index)
            print(self.f1)
            print(self.f2)
            print(face_id)


    def __str__(self):
        return(str(self.index))

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.rinstances = []
        cls.bl_instances = {}

    @classmethod
    def new_edge(cls, v1, v2, smooth, bl_index, bl_edge):
        self = cls(v1, v2, smooth, bl_index, bl_edge)
        # Check if a GDL edge already exists for this Blender edge (same or reversed direction).
        if len(cls.rinstances):
            is_present, edge = self.is_present(cls.bl_instances, self)
        else:
            is_present = False
            edge = None

        # Case 1: No existing edge for this Blender edge → register as a new canonical edge (positive index).
        if not is_present and not edge:
            cls.instances.append(self)
            cls.rinstances.insert(0, self)
            setattr(self, "index", (cls.instances.index(self)+1))  # GDL indices are 1-based.
            if not cls.bl_instances.get(bl_edge):
                cls.bl_instances[bl_edge] = [self]
            else:
                cls.bl_instances[bl_edge].append(self)
            return self, None

        # Case 2: Mirror edge found (same Blender edge, reversed winding) → assign negative index.
        # GDL uses negative edge index to indicate reversed traversal direction.
        elif not is_present and edge is not None:
            cls.rinstances.insert(0, self)
            if not cls.bl_instances.get(bl_edge):
                cls.bl_instances[bl_edge] = [self]
            else:
                cls.bl_instances[bl_edge].append(self)
            setattr(self, "index", (cls.instances.index(edge)+1) * -1)
            return self, edge

        # Case 3: Exact duplicate → return existing edge.
        else: return edge, None

    @classmethod
    def get_output(cls):
        # GDL EDGE format: EDGE v1, v2, face1, face2, status_bits
        # Status bits: 2 = smooth shading, 262144 = hard edge (visible crease), 0 = boundary/unshared edge.
        # TEVE indices are 1-based in GDL (hence +1).
        output_list = [
            f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, {edge.f1}, {edge.f2}, {(2 if edge.smooth else 262144) if edge.f2 and edge.f1 else 0}   !#{edge.index}"
            for edge in cls.instances
        ]
        return output_list

    @staticmethod
    def is_present(bl_instances, self):
        # Returns (True, edge) if exact match, (False, edge) if reversed match, (False, None) if not found.
        edges = bl_instances.get(self.bl_edge, [])
        for edge in edges:
            if self.v1.index == edge.v1.index and self.v2.index == edge.v2.index:
                return True, edge   # Exact duplicate
            elif self.v1.index == edge.v2.index and self.v2.index == edge.v1.index:
                return False, edge  # Mirror (reversed winding)
        return False, None


# Module-level globals accumulate GDL output during a single run_script() call.
# All are reset at the start and end of run_script() to avoid stale data across exports.
PGON = []           # GDL PGON commands (one per face, grouped per material)
VECT_LIST = []      # GDL VECT commands (face normals) - currently unused (use_vect=False)
MATERIAL = []       # GDL DEFINE MATERIAL commands
MATERIAL_ASSIGN = []# GDL BASE + SET MATERIAL blocks (with surface override logic)
TEXTURE = []        # GDL DEFINE TEXTURE commands
Textures_ids = {}   # {index: "filename.png"} - texture index map for XML embedding
converted_materials = []  # Tracks material names already processed (dedup guard)
material_cache = {}       # Maps material name → diffuse_color for legacy non-node materials
face_id_bl2ac = {}        # Blender face index → GDL face index mapping (unused currently)

def compare_verts_x_y_z(vert, previous_vert):
    if previous_vert is None:
        return False
    if vert[0] == previous_vert.x and vert[1] == previous_vert.y and vert[2] == previous_vert.z:
        return True
    else:
        return False


def set_materials(ob, save_directory):
    global PGON
    global VECT_LIST
    global MATERIAL
    global MATERIAL_ASSIGN
    global TEXTURE
    global Textures_ids
    global converted_materials
    global material_cache

    for mat_index, mat_slot in enumerate(ob.material_slots):
        material_exists = False
        # Prevents invalid and duplicated materials
        if mat_slot.material and not mat_slot.material.name in converted_materials:
            converted_materials.append(mat_slot.material.name)
            # create a list of PGON for each material
            PGON.append([])
            texture_name = None
            principled_node = None
            mat_name = utils.cleanString(mat_slot.material.name)

            # Walk the material node tree to find a Principled BSDF.
            # If found, check if Base Color (input[0]) has a connected Image Texture node.
            if mat_slot.material.node_tree:
                for node in mat_slot.material.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        principled_node = node
                        for node_links in principled_node.inputs[0].links:
                            texture_node = node_links.from_node
                            if texture_node.image:
                                texture_name = texture_node.image.name
                                break

            # Save the texture image as PNG to the textures folder.
            # LP_XMLConverter will embed it into the .gsm file.
            if texture_name:
                texture_datablock = bpy.data.images[texture_name]
                texture_datablock.save_render(save_directory + "\\" + texture_name + ".png")


            if texture_name:
                # GDL DEFINE TEXTURE: name, index, x_scale, y_scale, rotation_angle, status
                # Texture index is 1-based and must match the SubIdent in the XML <GDLPict> tag.
                if not f"{texture_name}.png" in Textures_ids.values():
                    TEXTURE.append(f'DEFINE TEXTURE "{texture_name}" {len(Textures_ids) + 1} , 1, 1, 1, 0')
                    Textures_ids[len(Textures_ids) + 1] = f"{texture_name}.png"
                # GDL DEFINE MATERIAL type 21 = textured material. IND(TEXTURE, name) resolves to the texture index.
                MATERIAL.append(f'''
DEFINE MATERIAL "material_{mat_name}" 21, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, IND(TEXTURE, "{texture_name}" )
                    ''')
            elif principled_node:
                # Extract material properties from Principled BSDF inputs.
                # Input indices are fixed positions in Blender's Principled BSDF node (Blender 3.x layout):
                #   [0]=Base Color, [3]=IOR, [4]=Alpha, [26]=Emission Color, [27]=Emission Strength
                # WARNING: These input indices may shift between Blender versions.
                color = principled_node.inputs[0].default_value
                ior = principled_node.inputs[3].default_value
                alpha = principled_node.inputs[4].default_value
                emission = principled_node.inputs[26].default_value
                emission_str = principled_node.inputs[27].default_value

                # Convert IOR to GDL specular coefficient using Fresnel formula:
                # reflectance at normal incidence: r = ((n-1)/(n+1))^2
                # GDL specular range is 0..1 where 0.08 ≈ IOR 1.5 (typical plastic/glass)
                iorb = (ior-1)/(ior+1)
                spec = (iorb*iorb)/0.08

                MATERIAL.append(f'''
DEFINE MATERIAL "material_{mat_name}" 0, {color[0]}, {color[1]}, {color[2]}, 1, 1, {spec}, {(alpha * -1) + 1},  {emission_str*100}, {((alpha * -1) + 1)*4}, {spec}, {spec}, {spec}, {emission[0]*emission_str}, {emission[1]*emission_str}, {emission[2]*emission_str}, {emission_str*65.5}
                    ''')

            else:
                rgb = None
                if hasattr(mat_slot.material, "diffuse_color"):
                    rgb = mat_slot.material.diffuse_color[:-1]
                    for name, values in material_cache.items():
                        if rgb == values:
                            mat_name = name
                            material_exists = True
                            rgb = False
                    if not material_exists:
                        material_cache[mat_slot.material.name] = mat_slot.material.diffuse_color[:-1]

                if rgb is not None:
                    if rgb:
                        MATERIAL.append(f'''
    DEFINE MATERIAL "material_{mat_name}" 0, {rgb[0]}, {rgb[1]}, {rgb[2]}, 1, 1, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

                        ''')
                    else:
                         MATERIAL.append('')
                else:
                    MATERIAL.append(f'''
    DEFINE MATERIAL "material_{mat_name}" 0, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

                        ''')
            
            # GDL surface override pattern: if the Archicad parameter sf_<matname> is 0,
            # use the embedded GDL material. Otherwise use the Archicad surface override value.
            # This allows users to swap surfaces directly in Archicad without re-exporting.
            MATERIAL_ASSIGN.append(f'''
BASE
IF sf_{mat_name} = 0 then
    SET MATERIAL "material_{mat_name}"
ELSE
    SET MATERIAL sf_{mat_name}
ENDIF
                ''')

    if not len(MATERIAL):
        # Fallback: object has no materials at all → use a plain white default.
        MATERIAL.append(f'''
DEFINE MATERIAL "material_default" 0, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        ''')

        MATERIAL_ASSIGN.append(f'''
BASE
IF sf_material_default = 0 then
    SET MATERIAL "material_default"
ELSE
    SET MATERIAL sf_material_default
ENDIF
        ''')
        PGON.append([])


def run_script(smooth_angle, save_directory, ob):
    # NOTE: ob must be in EDIT MODE (bmesh.from_edit_mesh) when this is called.
    # The caller (operators.py) enters edit mode before calling this function.

    # use_vect=False: VECT (face normal) commands are not currently used.
    # GDL supports explicit normals for lighting, but they're optional and add size to the script.
    use_vect = False

    global PGON
    global VECT_LIST
    global MATERIAL
    global MATERIAL_ASSIGN
    global TEXTURE
    global converted_materials
    global face_id_bl2ac
    global Textures_ids
    global material_cache

    # Reset all globals to prevent contamination from a previous export.
    PGON = []
    VECT_LIST = []
    MATERIAL = []
    MATERIAL_ASSIGN = []
    TEXTURE = []
    converted_materials = []
    face_id_bl2ac = {}
    Textures_ids = {}
    material_cache = {}


    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer= bm.loops.layers.uv.verify()  # Ensure a UV layer exists; creates one if absent.
    VECT_ID = 0


    # Build GDL DEFINE MATERIAL / DEFINE TEXTURE blocks from all material slots.
    set_materials(ob, save_directory)
    new_file = TEXTURE + MATERIAL  # Textures must be defined before materials that reference them.

    # Process geometry per material. Each material gets its own BODY section in GDL.
    # TEVE and EDGE indices are reset per material so each BODY is self-contained.
    for m_index, mat in enumerate(MATERIAL):
        TEVE.clear()
        EDGE.clear()
        PGON = []
        VECT_LIST = []

        faces = [f for f in bm.faces if f.material_index == m_index]
        # For each face in the mesh
        for face in faces:
            face_vertices = {}
            face_edges = {}

            max_n_loop = len(face.loops) - 1
            # Iterate face loops. In bmesh, a "loop" is a corner of the face:
            # it links a vertex, an edge, and a face together with UV data.
            for n_loop, loop in enumerate(face.loops):
                # Create a TEVE for the loop's vertex (includes UV from this specific corner).
                # The same 3D vertex can appear multiple times with different UVs (UV seams).
                face_vertices[n_loop] = TEVE.new_teve(
                    "%.4f" % loop.vert.co[0],
                    "%.4f" % loop.vert.co[1],
                    "%.4f" % loop.vert.co[2],
                    "%.4f" % loop[uv_layer].uv[0],
                    "%.4f" % loop[uv_layer].uv[1],
                    loop.vert.index
                )

                # An edge is smooth if: (a) Blender marks it as smooth, AND (b) the dihedral
                # angle between adjacent faces is ≤ smooth_angle threshold.
                # `calc_face_angle(99)` returns 99 as fallback for boundary edges (no second face).
                smooth = loop.edge.smooth and loop.edge.calc_face_angle(99) <= smooth_angle if loop.edge.smooth else False

                        
                # If not last edge of face
                # Create a TEVE with second vertice XYZUV infos (last one loops with first one)
                if not n_loop == max_n_loop:
                    face_vertices[n_loop+1] = TEVE.new_teve(
                        "%.4f" % face.loops[n_loop+1].vert.co[0],
                        "%.4f" % face.loops[n_loop+1].vert.co[1],
                        "%.4f" % face.loops[n_loop+1].vert.co[2],
                        "%.4f" % face.loops[n_loop+1][uv_layer].uv[0],
                        "%.4f" % face.loops[n_loop+1][uv_layer].uv[1],
                        loop.vert.index
                    )
                    
                    edge, existing_edge = EDGE.new_edge(face_vertices[n_loop], face_vertices[n_loop+1], smooth, loop.edge.index, loop.edge)
                    
                    face_edges[loop.edge.index] = edge
                    
                    if existing_edge:
                        edge = existing_edge
                    edge.add_face(len(PGON)+1)

                else:
                    face_vertices[0] = TEVE.new_teve(
                        "%.4f" % face.loops[0].vert.co[0],
                        "%.4f" % face.loops[0].vert.co[1],
                        "%.4f" % face.loops[0].vert.co[2],
                        "%.4f" % face.loops[0][uv_layer].uv[0],
                        "%.4f" % face.loops[0][uv_layer].uv[1],
                        loop.vert.index
                    )  
                    
                    edge, existing_edge = EDGE.new_edge(face_vertices[n_loop], face_vertices[0], smooth,  loop.edge.index, loop.edge) 
                    face_edges[loop.edge.index] = edge
                    if existing_edge:
                        edge = existing_edge
                    edge.add_face(len(PGON)+1)

            
            if use_vect:
                VECT_ID += 1 # starts at 0 in python, but at 1 in gdl. so it's ok to let it here
                VECT = f"VECT %.5f, %.5f, %.5f" % (face.normal[0], face.normal[1] ,face.normal[2])
                VECT_LIST.append(VECT)

            # GDL PGON format: PGON n_edges, vect_id, status, edge1, edge2, ...
            # vect_id=0 means no explicit normal (GDL calculates it). status=2 = visible face.
            pgon_str = f"PGON {str(len(face.edges))}, {VECT_ID if use_vect else 0}, 2, "
            # Wrap long PGON lines at 240 chars to stay within GDL line length limits.
            str_counter = 0
            for edge in face_edges.values():
                str_edge = str(edge)
                str_counter += len(str_edge) + 2
                if str_counter >= 240:
                    pgon_str += "\n"
                    str_counter = 0
                pgon_str += str_edge + ", "

            PGON.append(pgon_str[:-2])  # Strip trailing ", " from the last edge

        TEVE_LIST = TEVE.get_output()
        EDGE_LIST = EDGE.get_output()

        new_file.append(MATERIAL_ASSIGN[m_index])
        new_file += TEVE_LIST + EDGE_LIST
        if use_vect:
            new_file += VECT_LIST
        new_file += PGON
        new_file.append("BODY 1")

    # z_shift is the vertical offset applied in the XML 3D script via ADDZ to bring the
    # model's lowest point to Z=0 (Archicad expects objects to sit on the floor plane).
    z_shift = TEVE.min_z * -1

    # Save texture IDs before clearing, then clean up all module state.
    _textures_ids = Textures_ids
    TEVE.clear()
    EDGE.clear()
    PGON = []
    VECT_LIST = []
    MATERIAL = []
    MATERIAL_ASSIGN = []
    TEXTURE = []
    Textures_ids = {}
    converted_materials = []
    face_id_bl2ac = {}
    material_cache = {}

    # Returns: (list_of_gdl_lines, texture_id_dict, z_shift_value)
    return new_file, _textures_ids, z_shift