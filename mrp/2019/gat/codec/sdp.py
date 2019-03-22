from pathlib import Path;

from graph import Graph;

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

def matrix2graph(matrix, text = None):
    graph = Graph(matrix[0][0][1:])
    predicates = []
    for id, row in enumerate(matrix[1:]):
        lemma, pos, frame, top = row[2], row[3], row[6], row[4] == '+'
        if lemma == "_": lemma = row[1]
        properties = {"pos": pos}
        if frame != "_": properties["frame"] = frame
        node = graph.add_node(id, label=lemma, properties=properties, top=top, anchors=row[1])
        if row[5] == '+':
            predicates.append(id)
    for tgt, row in enumerate(matrix[1:]):
        for pred, label in enumerate(row[7:]):
            if label != '_':
                src = predicates[pred]
                edge = graph.add_edge(src, tgt, label)
    if text:
        id = graph.id;
        if isinstance(text, Path):
            file = text / (str(graph.id) + ".txt");
            if not file.exists():
                print("instance2graph(): no text for {}.".format(file),
                      file = sys.stderr);
            else:
                with file.open() as stream:
                    input = stream.readline();
                    if input.endswith("\n"): input = input[:len(input) - 1];
                    graph.input = input;
        else:
            input = text.get(id);
            if input:
                graph.input = input;
            else:
                print("instance2graph(): no text for key {}.".format(id),
                      file = sys.stderr);
    if graph.input:
        input = graph.input;
        n = len(input);
        i = 0;

        def skip():
            nonlocal i;
            while i < n and input[i] in {" ", "\t"}:
                i += 1;
        def scan(candidates):
            for candidate in candidates:
                if input.startswith(candidate, i):
                    return len(candidate);

        skip();
        for node in graph.nodes:
            if isinstance(node.anchors, str):
                form = node.anchors;
                m = None;
                if input.startswith(form, i):
                    m = len(form);
                else:
                    for old, new in {("‘", "`"), ("’", "'")}:
                        form = form.replace(old, new);
                        if input.startswith(form, i):
                            m = len(form);
                            break;
                if not m:
                    m = scan({"“", "\"", "``"}) or scan({"‘", "`"}) \
                        or scan({"”", "\"", "''"}) or scan({"’", "'"}) \
                        or scan({"—", "—", "---", "--"}) \
                        or scan({"…", "...", ". . ."});
                if m:
                    node.anchors = [{"from": i, "to": i + m}];
                    i += m;
                    skip();
                else:
                    raise Exception("failed to anchor |{}| in |{}| ({})".format(form, input, i));
    #
    # finally, purge singleton (isolated) nodes
    #
    graph.nodes = [node for node in graph.nodes if not node.is_singleton()];
    return graph

def read(fp, text = None):
    for matrix in read_matrices(fp):
        yield matrix2graph(matrix, text = text)
