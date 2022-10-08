import bpy
import bmesh
import subprocess
import sys
from math import *

#if not False:
#    subprocess.check_call([sys.executable, "-m", "pip", "install", "numba"])
#from numba import jit


filepath = "C:\\Users\\Asloric\\Desktop\\tempfile.txt"
target_filepath = "C:\\Users\\Asloric\\Desktop\\target.txt"
smooth_angle = 1.0 #  0.1 radian 5.7 degrees


# 


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

    def __init__(self, v1, v2, smooth, bl_index):
        self.bl_index = bl_index
        self.v1 = v1
        self.v2 = v2
        self.smooth = smooth 


    def __str__(self):
        return(str(self.index))
        return(f"{self.index}:  {self.v1.index}, {self.v2.index}")

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.rinstances = []

    @classmethod
    def new_edge(cls, v1, v2, smooth, bl_index):
        self = cls(v1, v2, smooth, bl_index)
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
            return self
        
        # if mirroring edge is found, 
        elif not is_present and edge is not None:
            print("DEBUG")
            self.__class__.instances.append(self)
            self.__class__.rinstances.insert(0, self)
            setattr(self, "index", (self.__class__.instances.index(edge)+1) * -1)
            return self

        else: return edge

    @classmethod
    def print(cls, edge = None):
        for edge in cls.instances:
            print(f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, -1, -1, {1 if edge.smooth else 0}   !{edge.bl_index}     {edge.index}")

    @classmethod
    def get_output(cls, edge = None):
        list = []
        for edge in cls.instances:
            list.append(f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, -1, -1, {1 if edge.smooth else 0}   !{edge.bl_index}     {edge.index} ")
        return list

    @staticmethod
    def is_present(rinstances, self):
        for edge in rinstances:
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


def compare_verts_x_y_z(vert, previous_vert):
    if previous_vert is None:
        return False
    if vert[0] == previous_vert.x and vert[1] == previous_vert.y and vert[2] == previous_vert.z:
        return True
    else:
        return False

def convert_to_archicad():
    with cProfile.Profile() as pr:
        run_script()
    with open('profiling_stats.txt', 'w') as stream:
            stats = Stats(pr, stream=stream)
            stats.strip_dirs()
            stats.sort_stats('time')
            stats.dump_stats('.prof_stats')
            stats.print_stats()

def run_script():
    global filepath
    global target_filepath
    global smooth_angle
    
    global PGON
    global VECT_LIST
    ob = bpy.context.active_object
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer= bm.loops.layers.uv.verify()
    VECT_ID = 0
    

    # For each face in the mesh
    for face in bm.faces:
        print("Face number %s" %face.index)

        face_vertices = {}
        face_edges = {}

        # For each loop in the face (loop = edge)
        for n_loop, loop in enumerate(face.loops):
            # Create a TEVE with first vertice XYZUV infos
            face_vertices[n_loop] = TEVE.new_teve(
                "%.3f" % loop.vert.co[0],
                "%.3f" % loop.vert.co[1],
                "%.3f" % loop.vert.co[2],
                "%.3f" % loop[uv_layer].uv[0],
                "%.3f" % loop[uv_layer].uv[1],
                loop.vert.index
            )
            print(loop.vert.index)
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
                    "%.3f" % face.loops[n_loop+1].vert.co[0],
                    "%.3f" % face.loops[n_loop+1].vert.co[1],
                    "%.3f" % face.loops[n_loop+1].vert.co[2],
                    "%.3f" % face.loops[n_loop+1][uv_layer].uv[0],
                    "%.3f" % face.loops[n_loop+1][uv_layer].uv[1],
                    loop.vert.index
                )
                #for i in dir(loop.edge):
                #    print(i)
                                    
                face_edges[loop.edge.index] = EDGE.new_edge(face_vertices[n_loop], face_vertices[n_loop+1], smooth, loop.edge.index) 

            else:
                face_vertices[0] = TEVE.new_teve(
                    "%.3f" % face.loops[0].vert.co[0],
                    "%.3f" % face.loops[0].vert.co[1],
                    "%.3f" % face.loops[0].vert.co[2],
                    "%.3f" % face.loops[0][uv_layer].uv[0],
                    "%.3f" % face.loops[0][uv_layer].uv[1],
                    loop.vert.index
                )  

                face_edges[loop.edge.index] = EDGE.new_edge(face_vertices[n_loop], face_vertices[0], smooth,  loop.edge.index) 

        
        VECT_ID += 1 # starts at 0 in python, but at 1 in gdl. so it's ok to let it here
        VECT = f"VECT %.5f, %.5f, %.5f" % (face.normal[0], face.normal[1] ,face.normal[2])
        
        
        #pgon_str = f"PGON {str(len(face.edges))}, {VECT_ID}, 0, "
        pgon_str = f"PGON {str(len(face.edges))}, 0, 0, "
        for edge in face_edges.values():
            pgon_str += str(edge) + ", "S
        VECT_LIST.append(VECT)
        PGON.append(pgon_str[:-2])
        print(pgon_str[:-2])

    teve_list = TEVE.get_output()
    edge_list = EDGE.get_output()


    new_file = teve_list + edge_list + PGON#  + VECT_LIST + PGON



    print("writing file...")
    with open(target_filepath, 'w') as target_file:
        for item in new_file:
            target_file.write("%s\n" % item)
    print("file saved to " + target_filepath)

    TEVE.clear()
    EDGE.clear()
    PGON = []
    
run_script()