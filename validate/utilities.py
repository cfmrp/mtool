import sys;

def report(graph, message, node = None, edge = None, stream = sys.stderr):
    if node: node = "; node #{}".format(node.id);
    if edge:
        edge = "; edge {} -{}-> {}".format(edge.src, edge.tgt,
                                           edge.lab if edge.lab else "");
    print("validate(): graph ‘{}’{}{}: {}"
          "".format(graph.id, node, edge, message), file = stream);
