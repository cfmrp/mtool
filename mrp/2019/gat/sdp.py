from analyzer import Graph, analyze_cmd

def read_matrix(file):
    rows = []
    for line in file:
        line = line.rstrip()
        if len(line) == 0:
            return rows
        else:
            rows.append(line.split("\t"))
    return None

def read_matrices(file):
    file.readline().rstrip()
    matrix = read_matrix(file)
    while matrix:
        yield matrix
        matrix = read_matrix(file)

def matrix2graph(matrix):
    graph = Graph(matrix[0][0][1:])
    predicates = []
    for id, row in enumerate(matrix[1:]):
        node = graph.add_node()
        node.is_top = row[4] == '+'
        if row[5] == '+':
            predicates.append(id)
    for tgt, row in enumerate(matrix[1:]):
        for pred, label in enumerate(row[7:]):
            if label != '_':
                src = predicates[pred]
                edge = graph.add_edge(src, tgt, label)
    graph.tokens = [columns[1] for columns in matrix[1:]]
    return graph

def read_sdp(fp):
    for matrix in read_matrices(fp):
        yield matrix2graph(matrix)

