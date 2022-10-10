import bpy
import bmesh
from math import *

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
    if len(newstring) > 28:
        return newstring[0:28] # max archicad lenght is 36. minus the ovr_sf_{mat_name}
    else:
        return newstring


class TEVE():
    instances = []
    rinstances = []
    def __init__(self, x,y,z,u,v, index) -> None:
        self.index = index
        self.x = x
        self.y = y
        self.z = z
        self.u = u
        self.v = v
        self.hash = self.__hash()


    @classmethod
    def clear(cls):
        cls.instances = []
        cls.rinstances = []

    @classmethod
    def new_teve(cls, x,y,z,u,v, index):
        self = cls(x,y,z,u,v, index)
        is_present = self.is_present(self)
        if is_present == False:
            self.__class__.instances.append(self)
            self.__class__.rinstances.insert(0, self)
            setattr(self, "index", self.__class__.instances.index(self))
            return self
        else: return is_present

    @classmethod
    def print(cls):
        for teve in cls.instances:
            print(f"TEVE {teve.x}, {teve.y}, {teve.z}, {teve.u}, {teve.v}   !{teve.index}")

    @classmethod
    def get_output(cls):
        list = []
        for teve in cls.instances:
            list.append(f"TEVE {teve.x}, {teve.y}, {teve.z}, {teve.u}, {teve.v}   !{teve.index}")
        return list

    @classmethod
    def is_present(cls, self):
        for teve in self.__class__.rinstances:
            if self.x == teve.x:
                if self.y == teve.y:
                    if self.z == teve.z:
                        if self.u == teve.u:
                            if self.v == teve.v:
                                return teve

        return False

    def __hash(self):
        return hash((self.x, self.y, self.z, self.u, self.v))


  
class EDGE():
    instances = []
    rinstances = []

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
        return(f"{self.index}:  {self.v1.index}, {self.v2.index}")

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.rinstances = []

    @classmethod
    def new_edge(cls, v1, v2, smooth, bl_index, bl_edge):
        self = cls(v1, v2, smooth, bl_index, bl_edge)
        # Get the mirroring edge if exists
        if len(self.__class__.rinstances):
            is_present, edge = self.is_present(self.__class__.rinstances, self)
        else:
            is_present = False
            edge = None
            
        # If no mirroring edge, create instance and return self
        if is_present == False and edge is None:
            self.__class__.instances.append(self)
            self.__class__.rinstances.insert(0, self)
            setattr(self, "index", (self.__class__.instances.index(self)+1))
            return self, None
        
        # if mirroring edge is found, 
        elif not is_present and edge is not None:
            #self.__class__.instances.append(self)
            self.__class__.rinstances.insert(0, self)
            setattr(self, "index", (self.__class__.instances.index(edge)+1) * -1)

            return self, edge

        else: return edge, None

    @classmethod
    def print(cls, edge = None):
        for edge in cls.instances:
            double_face = False
            smooth = 262146
            if edge.f2 and edge.f1:
                double_face = True
            if edge.smooth:
                smooth = 1
            elif double_face:
                smooth = 262146
            else:
                smooth = 0
            
            print(f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, {edge.f1}, {edge.f2}, {smooth}   !#{edge.index}")

    @classmethod
    def get_output(cls, edge = None):
        list = []
        for edge in cls.instances:
            double_face = False
            smooth = 262146
            if edge.f2 and edge.f1:
                double_face = True
            if edge.smooth:
                smooth = 262146
            elif double_face:
                smooth = 262146
            else:
                smooth = 262146
                
            list.append(f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, {edge.f1}, {edge.f2}, {smooth}   !#{edge.index}")
        return list

    @staticmethod
    def is_present(rinstances, self):
        for edge in rinstances:
            if edge.bl_edge == self.bl_edge:
                if self.v1.index in [edge.v1.index,edge.v2.index]:
                    if self.v2.index in [edge.v1.index,edge.v2.index]:
                        if self.v1.index == edge.v1.index and self.v2.index == edge.v2.index:
                            return True, edge
                        elif self.v1.index == edge.v2.index and self.v2.index == edge.v1.index:
                            return False, edge
        else:
            return False, None

    def __hash(self):
        return hash((self.v1, self.v2))

    def __rhash(self):
        return hash((self.v2, self.v1))

PGON = []
VECT_LIST = []
MATERIAL = []
MATERIAL_ASSIGN = []
TEXTURE = []

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

    for mat_slot in ob.material_slots:
        if mat_slot.material:
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
                texture_datablock.save_render(save_directory + texture_name + ".png")

            
            if texture_name:
                TEXTURE.append(f'DEFINE TEXTURE "{texture_name}" "{texture_name}.png", 1, 1, 1, 0')
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
            
        # For each face in the mesh
        for face in bm.faces:
            if face.material_index == m_index:
                face_vertices = {}
                face_edges = {}

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
                    edge_angle = loop.edge.calc_face_angle(99)
                    if edge_angle == 99:
                        smooth = None
                    elif edge_angle <= smooth_angle:
                        smooth = True
                    else:
                        smooth = False
                    
                    smooth = False if not loop.edge.smooth else smooth
                            
                            
                    # If not last edge of face
                    # Create a TEVE with second vertice XYZUV infos (last one loops with first one)
                    if not n_loop == len(face.loops) -1:
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

    TEVE.clear()
    EDGE.clear()
    PGON = []
    VECT_LIST = []
    MATERIAL = []
    MATERIAL_ASSIGN = []
    TEXTURE = []
    return new_file