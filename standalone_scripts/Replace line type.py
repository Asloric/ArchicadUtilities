# Replace line type.py - Standalone GDL edge status batch replacer.
# NOT part of the Blender addon. Run directly.
#
# Purpose: Replace the line-type / status value on all EDGE commands in a GDL .txt file.
# Useful for bulk converting edge visibility mode in an existing GDL script.
#
# Edge status values:
#   0 = hard edge (visible crease)
#   1 = hidden (not shown)
#   2 = smooth (shaded, no visible edge)
#
# NOTE: There is a bug in the replacement logic below.
# The replace call: line.replace(f", {replace_by}\n", f", {replace_by}\n")
# replaces the string with itself (source == target), so it does nothing.
# The intended logic was probably to replace any existing final status value
# with replace_by, but the implementation is incorrect.
#
# NOTE: Hardcoded paths. Change before use.
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
