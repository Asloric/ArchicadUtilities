filepath = "C:\\Users\\Asloric\\PycharmProjects\\Convert archicad object\\tempfile.txt"
target_filepath = "C:\\Users\\Asloric\\PycharmProjects\\Convert archicad object\\target.txt"
keep_material = True

replace_by = 1
# 0 = hard edge
# 1 = hidden
# 2 = smooth



coord_filter = ["TEVE 0, 0, 0, 0, 0\n",
"TEVE 1, 0, 0, 1, 1\n",
"TEVE 0, 1, 0, 1, 1\n",
"TEVE 0, 0, 1, 1, 1\n"]


new_file = []
group_number = 0
total_group = 0
print("Reading file....")
with open(filepath) as file:
    while line := file.readline():
        if line.startswith("EDGE"):
            new_file.append(line.replace(f", {replace_by}\n", f", {replace_by}\n"))
        else:
            new_file.append(line)

print("writing file...")
with open(target_filepath, 'w') as target_file:
    for item in new_file:
        target_file.write(item)
print("file saved to " + target_filepath)
