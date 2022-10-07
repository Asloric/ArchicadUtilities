import numba
from numba.core import types
from numba import int64, float64
import numpy as np





filepath = "C:\\Users\\Asloric\\PycharmProjects\\Convert archicad object\\tempfile.txt"
target_filepath = "C:\\Users\\Asloric\\PycharmProjects\\Convert archicad object\\target.txt"
keep_material = True

coord_filter = ["TEVE 0, 0, 0, 0, 0\n",
"TEVE 1, 0, 0, 1, 1\n",
"TEVE 0, 1, 0, 1, 1\n",
"TEVE 0, 0, 1, 1, 1\n"]

@numba.jit(nopython=True, forceobj=False)
def DO_IT(vert_list,edge_list,pgon_list,
            vert_indexes= numba.typed.Dict.empty(types.int32,types.int32),
            removed_vert = numba.typed.Dict.empty(types.int32,types.int32),
            new_vert_list = numba.typed.List.empty_list([float64, float64,float64]),
            edge_indexes= numba.typed.Dict.empty(types.int32,types.int32),
            removed_edge = numba.typed.Dict.empty(types.int32,types.int32),
            new_edge_list = numba.typed.List.empty_list(float64),
            idx_offset = 0,
            vert_01 = (),
            vert_01_compare = (),
            vert_02 = (),
            vert_02_compare = (),
):


    # Remove duplicate verts and reassign idx
    # print("Step 1/5 - Removing useless vertices")
    for idx, vertex in enumerate(vert_list):
        for compare_idx, compare_vert in enumerate(vert_list):
            if idx < compare_idx and vertex == compare_vert:
                if not idx + 1 in list(removed_vert.keys()):
                    # those two vertex are identical.
                    idx_offset = 0
                    for removed_idx in removed_vert.keys():
                        if removed_idx < idx + 1:
                            # If there a idx less than the initial id, it means i have to decrease new idx by that number ammount
                            idx_offset += 1
                    vert_indexes[compare_idx + 1] = idx + 1 - idx_offset
                    removed_vert[compare_idx + 1] = idx + 1 - idx_offset
                    # print("new id of ", compare_idx + 1, " is ", idx + 1 - idx_offset)
        if not idx + 1 in list(removed_vert.keys()):
            idx_offset = 0
            for removed_idx in list(removed_vert.keys()):
                if removed_idx < idx + 1:
                    idx_offset += 1
            vert_indexes[idx + 1] = idx + 1 - idx_offset
            new_vert_list.append(vertex)
            # print("new id of ", idx + 1 , " is ", idx + 1 - idx_offset)

    # print("Step 2/5 - Replacing edges pass 1 of 2")
    replaced_edge_list = []
    # Reassign edges vert indx
    for edge in edge_list:
        if edge[0] in list(removed_vert.keys()) or edge[1] in list(removed_vert.keys()):
            replaced_edge_list.append([vert_indexes[edge[0]], vert_indexes[edge[1]], -1, -1, 2])
        else:
            replaced_edge_list.append([vert_indexes[edge[0]], vert_indexes[edge[1]], -1, -1, 2])

    # print("Step 3/5 - Replacing edges pass 3 of 2")

    # Remove duplicate edges
    for idx, edge, in enumerate(replaced_edge_list):
        for compare_idx, compare_edge in enumerate(replaced_edge_list):
            if idx < compare_idx:
                if not idx + 1 in list(removed_edge.keys()):
                    if edge[0] == compare_edge[0]:
                        if edge[1] == compare_edge[1]:
                            # print("similar edge")
                            idx_offset = 0
                            for removed_idx in list(removed_edge.keys()):
                                if removed_idx < idx + 1:
                                    # If there a idx less than the initial id, it means i have to decrease new idx by that number ammount
                                    idx_offset += 1
                            edge_indexes[compare_idx + 1] = idx + 1 - idx_offset
                            removed_edge[compare_idx + 1] = idx + 1 - idx_offset
                    if edge[0] == compare_edge[1]:
                        if edge[1] == compare_edge[0]:
                            # print("revered edge")
                            idx_offset = 0
                            for removed_idx in list(removed_edge.keys()):
                                if removed_idx < idx + 1:
                                    # If there a idx less than the initial id, it means i have to decrease new idx by that number ammount
                                    idx_offset += 1
                            edge_indexes[compare_idx + 1] = (idx + 1 - idx_offset) * -1
                            removed_edge[compare_idx + 1] = (idx + 1 - idx_offset) * -1
        if not idx + 1 in list(removed_edge.keys()):
            idx_offset = 0
            for removed_idx in list(removed_edge.keys()):
                if removed_idx < idx + 1:
                    idx_offset += 1
            edge_indexes[idx + 1] = idx + 1 - idx_offset
            new_edge_list.append(edge)

    # print("Step 4/5 - Replacing faces pass 1 of 2")
    fixed_edge_list = []
    for idx, edge, in enumerate(new_edge_list):
        for compare_idx, compare_edge in enumerate(new_edge_list):
            if idx != compare_idx:
                vert_01 = (new_vert_list[edge[0]-1][0], new_vert_list[edge[0]-1][1], new_vert_list[edge[0]-1][2])
                vert_01_compare = (new_vert_list[compare_edge[0]-1][0], new_vert_list[compare_edge[0]-1][1], new_vert_list[compare_edge[0]-1][2])

                vert_02 = (new_vert_list[edge[1] - 1][0], new_vert_list[edge[1] - 1][1], new_vert_list[edge[1] - 1][2])
                vert_02_compare = (new_vert_list[compare_edge[1] - 1][0], new_vert_list[compare_edge[1] - 1][1], new_vert_list[compare_edge[1] - 1][2])

                if vert_01 == vert_01_compare:
                    if vert_02 == vert_02_compare:
                        edge[4] = 1
                if vert_01 == vert_02_compare:
                    if vert_02_compare == vert_01_compare:
                        edge[4] = 1

        fixed_edge_list.append(edge)

    # print("Step 5/5 - Replacing faces pass 2 of 2")
    new_faces_list = []
    for idx, face in enumerate(pgon_list):
        face[3] = edge_indexes[face[3]]
        face[4] = edge_indexes[face[4]]
        face[5] = edge_indexes[face[5]]
        new_faces_list.append([3, 0, -1, face[3], face[4], face[5]])

    return new_vert_list, fixed_edge_list, new_faces_list

def JUST(vert_list, edge_list, pgon_list):
    vert_list = np.asarray(vert_list, dtype="float64")
    edge_list = numba.typed.List(edge_list)
    pgon_list = numba.typed.List(pgon_list)
    new_vert_list, fixed_edge_list, new_faces_list = DO_IT(vert_list, edge_list, pgon_list)
    group = []
    for idx, vert in enumerate(new_vert_list):
        group.append(f"TEVE {str(vert).lstrip('[').rstrip(']')}" + f"    !{idx+1}")

    for idx, edge in enumerate(fixed_edge_list):
        group.append(f"EDGE {str(edge).lstrip('[').rstrip(']')}" + f"    !{idx+1}")

    for face in new_faces_list:
        group.append(f"PGON {str(face).lstrip('[').rstrip(']')}")

    return group
    #for i in group:
    #    print(i)


new_file = []
group_number = 0
total_group = 0
print("Reading file....")
with open(filepath) as file:
    while line := file.readline():
        if line.startswith("BASE"):
            total_group += 1
with open(filepath) as file:
    while line := file.readline():
        if len(line) > 1:
            if line.startswith("BASE"):
                group_number +=1
                print(f"Treating polygon group {group_number} out of {total_group}")
                new_file.append(line.rstrip("\n"))
                vert_list = []

                # TEVE x, y, z, u, v
                edge_list = []
                # EDGE vert1, vert2, pgon1, pgon2, status
                pgon_list = []
                # PGON n, vect, status, edge1, edge2, ..., edgen
            elif line.startswith("TEVE"):
                if not line in coord_filter:
                    vert = line.lstrip("TEVE").split(",")
                    vert_list.append([float64(vert[0]), float64(vert[1]), float64(vert[2]), float64(vert[3]), float64(vert[4])])
            elif line.startswith("EDGE"):
                edge = line.lstrip("EDGE").split(",")
                edge_list.append([int(edge[0]), int(edge[1]), int(edge[2]), int(edge[3]), int(edge[4])])
            elif line.startswith("PGON"):
                pgon = line.lstrip("PGON").split(",")
                pgon_list.append([int(pgon[0]), int(pgon[1]), int(pgon[2]), int(pgon[3]), int(pgon[4]), int(pgon[5])])
            elif line.startswith("BODY"):
                group = JUST(vert_list, edge_list, pgon_list)
                for i in group:
                    new_file.append(i)
                new_file.append(line.rstrip("\n"))
            elif line.startswith("DEFINE MATERIAL") and "TEXTURE" in line:
                if keep_material == True:
                    mat = line.split('"')
                    new_material = f'{mat[0]} "{mat[1]}" 21, 1, 1, 1, 1, 1, 0.25, 0, 0, 0, 0, 0, IND(TEXTURE, "{mat[3]}")'
                    new_file.append(new_material)
                else:
                    new_file.append(line.rstrip("\n"))
            else:
                new_file.append(line.rstrip("\n"))

with open(target_filepath, 'w') as target_file:
    for item in new_file:
        target_file.write("%s\n" % item)

#for i in new_file:
#    print(i)