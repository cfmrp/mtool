from graph import Graph;

def read_matrix(file):
    rows = [];
    for line in file:
        line = line.rstrip();
        if len(line) == 0:
            return rows;
        else:
            rows.append(line.split("\t"));
    return rows or None

def read_matrices(file):
    file.readline().rstrip();
    matrix = read_matrix(file);
    while matrix:
        yield matrix;
        matrix = read_matrix(file);

def matrix2graph(matrix, framework = None, text = None):
    graph = Graph(matrix[0][0][1:], flavor = 0, framework = framework);
    predicates = [];
    for id, row in enumerate(matrix[1:]):
        lemma, pos, frame, top = row[2], row[3], row[6], row[4] == '+';
        if lemma == "_": lemma = row[1];
        properties = {"pos": pos};
        if frame != "_": properties["frame"] = frame;
        node = graph.add_node(id, label = lemma,
                              properties = list(properties.keys()),
                              values = list(properties.values()),
                              top = top, anchors = [row[1]] if text else None);
        if row[5] == '+':
            predicates.append(id);
    for tgt, row in enumerate(matrix[1:]):
        for pred, label in enumerate(row[7:]):
            if label != '_':
                src = predicates[pred];
                edge = graph.add_edge(src, tgt, label);
    if text:
        graph.add_input(text);
        graph.anchor();
    #
    # finally, purge singleton (isolated) nodes
    #
    graph.nodes = [node for node in graph.nodes if not node.is_singleton()];
    return graph;

def read(fp, framework = None, text = None):
    for matrix in read_matrices(fp):
        yield matrix2graph(matrix, framework, text), None;
