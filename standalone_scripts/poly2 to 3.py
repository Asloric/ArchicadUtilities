
filepath = "C:\\Users\\Asloric\\Desktop\\script.txt"
outfile = "C:\\Users\\Asloric\\Desktop\\scriptout.txt"
newfile = ""
with open(filepath, 'r') as file:
    next_line = False
    for line in file:
        if line.startswith("poly2_b{5}"):
            line_parts = line.split(",")
            line_part = line_parts[0].replace("poly2_b{5}", "poly_")
            newfile += line_part+ ",\n"
            next_line = True
        else:
            if next_line:
                next_line = False
            else:
                newfile += line
                next_line = False


with open(outfile, 'w') as file:
    file.write(newfile)