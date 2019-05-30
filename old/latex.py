import sys

#print("\\begin{tabular}{llrrrrrr}")
#print("\\toprule")
#print("& & \\multicolumn{1}{c}{\\textbf{\\CCD}} & \\multicolumn{1}{c}{\\textbf{\\DM}} & \\multicolumn{1}{c}{\\textbf{\\PSD}} & \\multicolumn{1}{c}{\\textbf{\\EDS}} & \\multicolumn{1}{c}{\\textbf{\\AMR}} & \\multicolumn{1}{c}{\\textbf{\\AMRup}}\\\\")
#print("\\midrule")

lines = []

with open(sys.argv[1]) as fp:
    for line in fp:
        columns = line.rstrip().split('\t')
        lines.append(columns[0] + " & " + columns[1])

for file in sys.argv[1:]:
    with open(file) as fp:
        for i, line in enumerate(fp):
            columns = line.rstrip().split('\t')
            lines[i] = lines[i] + " & " + columns[2]

for i, line in enumerate(lines):
    lines[i] = lines[i] + "\\\\"

print("\n".join(lines))
#print("\\bottomrule")
#print("\\end{tabular}")
