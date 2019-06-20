import sys;

import validate.amr;
import validate.eds;
import validate.sdp;
import validate.ucca;
from validate.utilities import report;

def test(graph, actions, stream = sys.stderr):
  n = 0;
  if "input" in actions:
    if not isinstance(graph.input, str) or len(graph.input) == 0:
      n += 1;
      report(graph, 
             "missing or invalid ‘input’ property",
             stream = stream);

  if "edges" in actions:
    #
    # the following is most likely redundant: the MRP input codec already has
    # to make sure all source and target identifiers actually exist.  maybe
    # add a type check (int), though?
    #
    nodes = {node.id: node for node in graph.nodes};
    for edge in graph.edges:
      if edge.src not in nodes:
        n += 1;
        report(graph,
               "invalid source",
               node = node, edge = edge,
               stream = stream);
      if edge.tgt not in nodes:
        n += 1;
        report(graph, 
               "invalid target",
               node = node, edge = edge,
               stream = stream);

  sdp = {"ccd", "dm", "pas", "psd"};
  if graph.framework == "amr" and "amr" in actions:
    n += validate.amr.test(graph, actions, stream);
  elif graph.framework == "eds" and "eds" in actions:
    n += validate.eds.test(graph, actions, stream);
  elif graph.framework in sdp and (sdp & actions):
    n += validate.sdp.test(graph, actions, stream);
  elif graph.framework == "ucca" and "ucca" in actions:
    n += validate.ucca.test(graph, actions, stream);

  return n;
