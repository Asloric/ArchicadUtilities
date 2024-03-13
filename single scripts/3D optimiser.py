Folder = "Mobilier"
Sub_folder1 = "Tables"
FIle_name = "BIBELO_SWIMM_Table Duo"
Lod = "0"

is_lod = True

keep_material = True
Use_soft_edges = True
# ATTENTION:  NE PAS UTILISER LES SOFT EDGE REND L'OBJET INVISIBLE EN RENDU CROQUIS!!!


















if is_lod:
    filepath = f"C:\\Users\\clovis.flayols\\Desktop\\05_Scripts\\{Folder}\\{Sub_folder1}\\{FIle_name}_LOD{Lod}.txt"
    target_filepath = f"C:\\Users\\clovis.flayols\\Desktop\\05_Scripts\\{Folder}\\{Sub_folder1}\\{FIle_name}_LOD{Lod}_opti.txt"
else:
    filepath = f"C:\\Users\\clovis.flayols\\Desktop\\05_Scripts\\{Folder}\\{Sub_folder1}\\{FIle_name}.txt"
    target_filepath = f"C:\\Users\\clovis.flayols\\Desktop\\05_Scripts\\{Folder}\\{Sub_folder1}\\{FIle_name}_opti.txt"


coord_filter = ["TEVE 0, 0, 0, 0, 0\n",
"TEVE 1, 0, 0, 1, 1\n",
"TEVE 0, 1, 0, 1, 1\n",
"TEVE 0, 0, 1, 1, 1\n"]

if Use_soft_edges:
    edge_n_end = 2
else:
    edge_n_end = 0

def DO_IT(vert_list,edge_list,pgon_list):
    vert_indexes = {}
    removed_vert = {}
    new_vert_list = []
    # Remove duplicate verts and reassign idx
    for idx, vert in enumerate(vert_list):
        for compare_idx, compare_vert in enumerate(vert_list):
            if idx < compare_idx and vert == compare_vert:
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
            new_vert_list.append(vert)
            # print("new id of ", idx + 1 , " is ", idx + 1 - idx_offset)

    replaced_edge_list = []
    # Reassign edges vert indx
    for edge in edge_list:
        if edge[0] in list(removed_vert.keys()) or edge[1] in list(removed_vert.keys()):
            replaced_edge_list.append([vert_indexes[edge[0]], vert_indexes[edge[1]], -1, -1, edge_n_end])
        else:
            replaced_edge_list.append([vert_indexes[edge[0]], vert_indexes[edge[1]], -1, -1, 1])


    edge_indexes = {}
    removed_edge = {}
    new_edge_list = []
    # Remove duplicate edges
    for idx, edge, in enumerate(replaced_edge_list):
        for compare_idx, compare_edge in enumerate(replaced_edge_list):
            if idx < compare_idx:
                if not idx + 1 in removed_edge.keys():
                    if edge[0] == compare_edge[0]:
                        if edge[1] == compare_edge[1]:
                            # print("similar edge")
                            idx_offset = 0
                            for removed_idx in removed_edge.keys():
                                if removed_idx < idx + 1:
                                    # If there a idx less than the initial id, it means i have to decrease new idx by that number ammount
                                    idx_offset += 1
                            edge_indexes[compare_idx + 1] = idx + 1 - idx_offset
                            removed_edge[compare_idx + 1] = idx + 1 - idx_offset
                    if edge[0] == compare_edge[1]:
                        if edge[1] == compare_edge[0]:
                            # print("revered edge")
                            idx_offset = 0
                            for removed_idx in removed_edge.keys():
                                if removed_idx < idx + 1:
                                    # If there a idx less than the initial id, it means i have to decrease new idx by that number ammount
                                    idx_offset += 1
                            edge_indexes[compare_idx + 1] = (idx + 1 - idx_offset) * -1
                            removed_edge[compare_idx + 1] = (idx + 1 - idx_offset) * -1
        if not idx + 1 in removed_edge.keys():
            idx_offset = 0
            for removed_idx in removed_edge.keys():
                if removed_idx < idx + 1:
                    idx_offset += 1
            edge_indexes[idx + 1] = idx + 1 - idx_offset
            new_edge_list.append(edge)

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

    new_faces_list = []
    for idx, face in enumerate(pgon_list):
        face[3] = edge_indexes[face[3]]
        face[4] = edge_indexes[face[4]]
        face[5] = edge_indexes[face[5]]
        new_faces_list.append([3, 0, -1, face[3], face[4], face[5]])


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
                    vert_list.append([float(vert[0]), float(vert[1]), float(vert[2]), float(vert[3]), float(vert[4])])
            elif line.startswith("EDGE"):
                edge = line.lstrip("EDGE").split(",")
                edge_list.append([int(edge[0]), int(edge[1]), int(edge[2]), int(edge[3]), int(edge[4])])
            elif line.startswith("PGON"):
                pgon = line.lstrip("PGON").split(",")
                pgon_list.append([int(pgon[0]), int(pgon[1]), int(pgon[2]), int(pgon[3]), int(pgon[4]), int(pgon[5])])
            elif line.startswith("BODY"):
                group = DO_IT(vert_list, edge_list, pgon_list)
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
                
print("Rewriting file")
with open(target_filepath, 'w') as target_file:
    for item in new_file:
        target_file.write("%s\n" % item)
print("Conversion completed")
print(f"FIle saved as {target_filepath}")

#for i in new_file:
#    print(i)