# poly2 to 3.py - Standalone GDL 2D polygon command converter.
# NOT part of the Blender addon. Run directly as a Python script.
#
# Purpose: Convert `poly2_b{5}` GDL commands to `poly_` format in a GDL script file.
# This is needed when porting 2D scripts between Archicad object types that expect
# different 2D polygon command variants.
#
# GDL command mapping:
#   poly2_b{5} n, status, pen, bgpen,   <- 5-parameter variant with fill colours
#   poly_        n, status,              <- simpler polygon, no colour parameters
#
# Conversion logic:
#   - Replaces "poly2_b{5}" with "poly_" in the command token
#   - Keeps only the first argument (vertex count) from the parameter list
#   - SKIPS the immediately following line (the status/pen/bgpen arguments line,
#     which is passed as a separate continuation line in some GDL formatters)
#
# NOTE: Hardcoded paths. Change before use.

filepath = "C:\\Users\\X\\Desktop\\script.txt"
outfile = "C:\\Users\\X\\Desktop\\scriptout.txt"
newfile = ""
with open(filepath, 'r') as file:
    next_line = False
    for line in file:
        if line.startswith("poly2_b{5}"):
            # Replace the command token and keep only the vertex count (first comma-delimited token).
            # The trailing ", \n" re-joins the truncated command to the next continuation.
            line_parts = line.split(",")
            line_part = line_parts[0].replace("poly2_b{5}", "poly_")
            newfile += line_part+ ",\n"
            # Flag to skip the NEXT line (the status/colour arguments line that no longer applies).
            next_line = True
        else:
            if next_line:
                # Skip the status/colour arguments line that followed poly2_b{5}.
                next_line = False
            else:
                newfile += line
                next_line = False


with open(outfile, 'w') as file:
    file.write(newfile)