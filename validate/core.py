import sys;

import validate.eds;
from validate.utilities import report;

def test(graph, actions, stream = sys.stderr):
  if "input" in actions:
    if not isinstance(graph.input, str) or len(graph.input) == 0:
      report(graph, 
             "invalid ‘input’ property",
             stream = stream);

  if "edges" in actions:
    nodes = {node.id: node for node in graph.nodes};
    for edge in graph.edges:
      if edge.src not in nodes:
        report(graph,
               "invalid source",
               node = node, edge = edge,
               stream = stream);
        if edge.tgt not in nodes:
          report(graph, 
                 "invalid target",
                 node = node, edge = edge,
                 stream = stream);

  if graph.framework == "eds" and "eds" in actions:
    validate.eds.test(graph, actions, stream);
