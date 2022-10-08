import bpy
import bmesh
import subprocess
import sys

#if not False:
#    subprocess.check_call([sys.executable, "-m", "pip", "install", "numba"])
#from numba import jit

import cProfile
from pstats import Stats, SortKey


class TEVE():
    instances = []
    rinstances = []
    def __init__(self, x,y,z,u,v) -> None:
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
    def new_teve(cls, x,y,z,u,v):
        self = cls(x,y,z,u,v)
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
            print(f"TEVE {teve.x}, {teve.y}, {teve.z}, {teve.u}, {teve.v}")

    @classmethod
    def get_output(cls):
        list = []
        for teve in cls.instances:
            list.append(f"TEVE {teve.x}, {teve.y}, {teve.z}, {teve.u}, {teve.v}")
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

    def __init__(self, v1, v2):
        self.v1 = v1
        self.v2 = v2


    def __str__(self):
        return(str(self.index))
        return(f"{self.index}:  {self.v1.index}, {self.v2.index}")

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.rinstances = []

    @classmethod
    def new_edge(cls, v1, v2):
        self = cls(v1, v2)
        if len(self.__class__.rinstances):
            is_present, edge = self.is_present(self.__class__.rinstances, self)
        else:
            is_present = False
            edge = None
        if is_present == False and edge is None:
            self.__class__.instances.append(self)
            self.__class__.rinstances.insert(0, self)
            setattr(self, "index", (self.__class__.instances.index(self)+1))
            return self
        elif not is_present and edge is not None:
            self.__class__.instances.append(self)
            self.__class__.rinstances.insert(0, self)
            setattr(self, "index", (self.__class__.instances.index(edge)+1) * -1)
            return self

        else: return edge

    @classmethod
    def print(cls, edge = None):
        for edge in cls.instances:
            print(f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, -1, -1, 0")

    @classmethod
    def get_output(cls, edge = None):
        list = []
        for edge in cls.instances:
            list.append(f"EDGE {edge.v1.index+1}, {edge.v2.index+1}, -1, -1, 0")
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
    global PGON
    ob = bpy.context.active_object
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer= bm.loops.layers.uv.verify()
       

    for face in bm.faces:
        face_vertices = {}
        face_edges = {}

        for n_loop, loop in enumerate(face.loops):
            face_vertices[n_loop] = TEVE.new_teve(
                "%.3f" % loop.vert.co[0],
                "%.3f" % loop.vert.co[1],
                "%.3f" % loop.vert.co[2],
                "%.3f" % loop[uv_layer].uv[0],
                "%.3f" % loop[uv_layer].uv[1],
            )

            if not n_loop == len(face.loops) -1:
                face_vertices[n_loop+1] = TEVE.new_teve(
                    "%.3f" % face.loops[n_loop+1].vert.co[0],
                    "%.3f" % face.loops[n_loop+1].vert.co[1],
                    "%.3f" % face.loops[n_loop+1].vert.co[2],
                    "%.3f" % face.loops[n_loop+1][uv_layer].uv[0],
                    "%.3f" % face.loops[n_loop+1][uv_layer].uv[1],
                )
            
                face_edges[loop.edge.index] = EDGE.new_edge(face_vertices[n_loop], face_vertices[n_loop+1]) 

            else:
                face_vertices[0] = TEVE.new_teve(
                    "%.3f" % face.loops[0].vert.co[0],
                    "%.3f" % face.loops[0].vert.co[1],
                    "%.3f" % face.loops[0].vert.co[2],
                    "%.3f" % face.loops[0][uv_layer].uv[0],
                    "%.3f" % face.loops[0][uv_layer].uv[1],
                )  

                face_edges[loop.edge.index] = EDGE.new_edge(face_vertices[n_loop], face_vertices[0]) 

        
        pgon_str = f"PGON {str(len(face.edges))}, 0, -1, "
        for edge in face_edges.values():
            pgon_str += str(edge) + ", "
        PGON.append(pgon_str[:-2])

    teve_list = TEVE.get_output()
    edge_list = EDGE.get_output()


    new_file = teve_list + edge_list + PGON

    filepath = "C:\\Users\\Asloric\\PycharmProjects\\Convert archicad object\\tempfile.txt"
    target_filepath = "C:\\Users\\Asloric\\Desktop\\target.txt"


    print("writing file...")
    with open(target_filepath, 'w') as target_file:
        for item in new_file:
            target_file.write("%s\n" % item)
    print("file saved to " + target_filepath)

    TEVE.clear()
    EDGE.clear()
    PGON = []