import sys;

def report(graph, message, node = None, edge = None, stream = sys.stderr):
  if node is not None:
    node = "; node #{}".format(node.id);
  else:
    node = "";
  if edge is not None:
    edge = "; edge {} -{}-> {}".format(edge.src, edge.tgt,
                                       edge.lab if edge.lab else "");
  else:
    edge = "";
  print("validate(): graph '{}'{}{}: {}"
        "".format(graph.id, node, edge, message), file = stream);
