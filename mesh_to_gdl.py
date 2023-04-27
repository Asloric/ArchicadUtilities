import bpy
import bmesh
from math import *
from .import local_dict

def cleanString(incomingString):
    newstring = incomingString
    newstring = newstring.replace("!","")
    newstring = newstring.replace("@","")
    newstring = newstring.replace("#","")
    newstring = newstring.replace("$","")
    newstring = newstring.replace("%","")
    newstring = newstring.replace("^","")
    newstring = newstring.replace("&","and")
    newstring = newstring.replace("*","")
    newstring = newstring.replace("(","")
    newstring = newstring.replace(")","")
    newstring = newstring.replace("+","")
    newstring = newstring.replace("=","")
    newstring = newstring.replace("?","")
    newstring = newstring.replace("\'","")
    newstring = newstring.replace("\"","")
    newstring = newstring.replace("{","")
    newstring = newstring.replace("}","")
    newstring = newstring.replace("[","")
    newstring = newstring.replace("]","")
    newstring = newstring.replace("<","")
    newstring = newstring.replace(">","")
    newstring = newstring.replace("~","")
    newstring = newstring.replace("`","")
    newstring = newstring.replace(":","")
    newstring = newstring.replace(";","")
    newstring = newstring.replace("|","")
    newstring = newstring.replace("\\","")
    newstring = newstring.replace("/","")        
    newstring = newstring.replace(".","")        
    newstring = newstring.replace(" ","_")        
    newstring = newstring.replace("é","e")        
    newstring = newstring.replace("è","e")        
    newstring = newstring.replace("à","a")        
    if len(newstring) > 28:
        return newstring[0:28] # max archicad lenght is 36. minus the ovr_sf_{mat_name}*
    else:
        if newstring.upper() in local_dict.gdl_keywords:
            return "bl_" + newstring
        return newstring


class TEVE():
    instances = []
    rinstances = []
    coords_dict = {} # Store coordinates to speed up "is present" function
    min_z = 0.0  # Used to shift model Up, to always have origin to ground level.

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
            setattr(self, "index", cls.instances.index(self))
            return self
        else: return is_present

    @classmethod
    def get_output(cls):
        list = []
        for teve in cls.instances:
            list.append(f"TEVE {teve.x}, {teve.y}, {teve.z}, {teve.u}, {teve.v}   !{teve.index}")
        return list

    @classmethod
    def is_present(cls, self):
        return cls.coords_dict.get((self.x, self.y, self.z, self.u, self.v))

  
class EDGE():
    instances = []
    rinstances = []
    bl_instances = {}

    def __init__(self, v1, v2, smooth, bl_index, bl_edge):
        self.bl_edge = bl_edge
        self.bl_index = bl_index
        self.f1 = -1
        self.f2 = -1
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
        # Get the mirroring edge if exists
        if len(cls.rinstances):
            is_present, edge = self.is_present(cls.bl_instances, self)
        else:
            is_present = False
            edge = None
            
        # If no mirroring edge, create instance and return self
        if not is_present and not edge:
            cls.instances.append(self)
            cls.rinstances.insert(0, self)
            setattr(self, "index", (cls.instances.index(self)+1))
            if not cls.bl_instances.get(bl_edge):
                cls.bl_instances[bl_edge] = [self]
            else:
                cls.bl_instances[bl_edge].append(self)
            return self, None
        
        # if mirroring edge is found, 
        elif not is_present and edge is not None:
            cls.rinstances.insert(0, self)
            if not cls.bl_instances.get(bl_edge):
                cls.bl_instances[bl_edge] = [self]
            else:
                cls.bl_instances[bl_edge].append(self)
            setattr(self, "index", (cls.instances.index(edge)+1) * -1)
            return self, edge

        else: return edge, None

    @classmethod
    def get_output(cls):
        output_list = [
            f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, {edge.f1}, {edge.f2}, {(2 if edge.smooth else 262144) if edge.f2 and edge.f1 else 0}   !#{edge.index}"
            for edge in cls.instances
        ]
        return output_list

    @staticmethod
    def is_present(bl_instances, self):
        edges = bl_instances.get(self.bl_edge, [])
        for edge in edges:
            if self.v1.index == edge.v1.index and self.v2.index == edge.v2.index:
                return True, edge
            elif self.v1.index == edge.v2.index and self.v2.index == edge.v1.index:
                return False, edge  
        return False, None


PGON = []
VECT_LIST = []
MATERIAL = []
MATERIAL_ASSIGN = []
TEXTURE = []
Textures_ids = {}
converted_materials = []
face_id_bl2ac = {}

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

    for mat_index, mat_slot in enumerate(ob.material_slots):
        # Prevents invalid and duplicated materials
        if mat_slot.material and not mat_slot.material.name in converted_materials:
            converted_materials.append(mat_slot.material.name)
            # create a list of PGON for each material
            PGON.append([])
            texture_name = None
            principled_node = None
            mat_name = cleanString(mat_slot.material.name)

            # Retrieve the diffuse texture
            for node in mat_slot.material.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    principled_node = node
                    for node_links in principled_node.inputs[0].links:
                        texture_node = node_links.from_node
                        if texture_node.image:
                            texture_name = texture_node.image.name
                            break

            
            # Save image to folder
            if texture_name:
                texture_datablock = bpy.data.images[texture_name]
                texture_datablock.save_render(save_directory + "\\" + texture_name + ".png")

            
            if texture_name:
                # TEXTURE.append(f'DEFINE TEXTURE "{texture_name}" "{texture_name}.png", 1, 1, 1, 0')
                if not f"{texture_name}.png" in Textures_ids.values():
                    TEXTURE.append(f'DEFINE TEXTURE "{texture_name}" {len(Textures_ids) + 1} , 1, 1, 1, 0')
                    Textures_ids[len(Textures_ids) + 1] = f"{texture_name}.png"
                MATERIAL.append(f'''
r = REQUEST{'{2}'} ("Building_Material_info", {mat_name}, "gs_bmat_surface", {mat_name})
DEFINE MATERIAL "material_{mat_name}" 21, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, IND(TEXTURE, "{texture_name}" )
                    ''')
            elif principled_node:
                color = principled_node.inputs[0].default_value
                spec = principled_node.inputs[7].default_value
                alpha = principled_node.inputs[21].default_value
                emission = principled_node.inputs[19].default_value
                emission_str = principled_node.inputs[20].default_value
                MATERIAL.append(f'''
r = REQUEST{'{2}'} ("Building_Material_info", {mat_name}, "gs_bmat_surface", sf_{mat_name})
DEFINE MATERIAL "material_{mat_name}" 0, {color[0]}, {color[1]}, {color[2]}, 1, 1, {spec}, {(alpha * -1) + 1},  {emission_str}, {(alpha * -1) + 1}, {spec}, {spec}, {spec}, {emission[0]}, {emission[1]}, {emission[2]}, {emission_str}
                    ''')

            else:
                MATERIAL.append(f'''
DEFINE MATERIAL "material_{mat_name}" 0, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
!bms_{mat_name} = 0
r = REQUEST{'{2}'} ("Building_Material_info", {mat_name}, "gs_bmat_surface", {mat_name})
                    ''')
            
            MATERIAL_ASSIGN.append(f'''
BASE
SET building_material {mat_name}, DEFAULT, DEFAULT
IF not(ovr_sf_{mat_name}) then
    SET MATERIAL "material_{mat_name}"
ELSE
    SET MATERIAL sf_{mat_name}
ENDIF
                ''')

    if not len(MATERIAL):
        MATERIAL.append(f'''
DEFINE MATERIAL "material_default" 0, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
!bms_material_default = 0
r = REQUEST{'{2}'} ("Building_Material_info", material_default, "gs_bmat_surface", material_default)
        ''')
        
        MATERIAL_ASSIGN.append(f'''
BASE
SET building_material material_default, DEFAULT, DEFAULT
IF not(ovr_sf_material_default) then
    SET MATERIAL "material_default"
ELSE
    SET MATERIAL sf_material_default
ENDIF
        ''')
        PGON.append([])


def run_script(smooth_angle, save_directory):
    use_vect = False
    
    global PGON
    global VECT_LIST
    global MATERIAL
    global MATERIAL_ASSIGN
    global TEXTURE
    global converted_materials
    global face_id_bl2ac
    global Textures_ids
    #Clear list
    converted_materials = []


    ob = bpy.context.active_object
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer= bm.loops.layers.uv.verify()
    VECT_ID = 0
    

    # for material index in object
    # create an ac_material from bl_material data
    set_materials(ob, save_directory)
    new_file = TEXTURE + MATERIAL

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
            # For each loop in the face (loop = edge)
            for n_loop, loop in enumerate(face.loops):
                # Create a TEVE with first vertice XYZUV infos
                face_vertices[n_loop] = TEVE.new_teve(
                    "%.4f" % loop.vert.co[0],
                    "%.4f" % loop.vert.co[1],
                    "%.4f" % loop.vert.co[2],
                    "%.4f" % loop[uv_layer].uv[0],
                    "%.4f" % loop[uv_layer].uv[1],
                    loop.vert.index
                )

                # Get the edge angle with other faces
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
            
            pgon_str = f"PGON {str(len(face.edges))}, {VECT_ID if use_vect else 0}, 2, "
            #pgon_str = f"PGON {str(len(face.edges))}, 0, 2, "
            for edge in face_edges.values():
                pgon_str += str(edge) + ", "

            # depending on the face material, tell this pgon to go in specific list
            PGON.append(pgon_str[:-2])

        TEVE_LIST = TEVE.get_output()
        EDGE_LIST = EDGE.get_output()

        new_file.append(MATERIAL_ASSIGN[m_index])
        new_file += TEVE_LIST + EDGE_LIST
        if use_vect:
            new_file += VECT_LIST
        new_file += PGON
        new_file.append("BODY 1")

    z_shift = TEVE.min_z * -1
    TEVE.clear()
    EDGE.clear()
    PGON = []
    VECT_LIST = []
    MATERIAL = []
    MATERIAL_ASSIGN = []
    TEXTURE = []
    _textures_ids = Textures_ids
    Textures_ids = {}
    converted_materials = []
    face_id_bl2ac = {}
    
    return new_file, _textures_ids, z_shift