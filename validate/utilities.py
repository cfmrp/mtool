import sys;

def report(graph, message, node = None, edge = None,
           framework = None, level = "E", stream = sys.stderr):
  if node is not None:
    node = "; node #{}".format(node.id);
  else:
    node = "";
  if edge is not None:
    edge = "; edge {} -{}-> {}".format(edge.src, edge.tgt,
                                       edge.lab if edge.lab else "");
  else:
    edge = "";
  if framework is not None:
    framework = "{{{}}} ".format(framework);
  else:
    framework = "";
  print("validate(): [{}] {}graph #{}{}{}: {}."
        "".format(level, framework, graph.id, node, edge, message),
        file = stream);
