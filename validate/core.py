import sys;

import validate.amr;
import validate.eds;
import validate.sdp;
import validate.ucca;
from validate.utilities import report;


def test(graph, actions, stream = sys.stderr):
  n = 0;
  if not isinstance(graph.id, str) or len(graph.id) == 0:
    n += 1;
    report(graph,
           "missing or invalid ‘id’ property",
           stream = stream);
  if not isinstance(graph.flavor, int) or graph.flavor not in {0, 1, 2}:
    n += 1;
    report(graph,
           "missing or invalid ‘flavor’ property",
           stream = stream);
  if not isinstance(graph.framework, str) or \
     graph.framework not in {"ccd", "dm", "pas", "psd", "ptg", "ud",
                             "eds", "ucca", "amr", "drg"}:
    n += 1;
    report(graph,
           "missing or invalid ‘framework’ property",
           stream = stream);
  elif graph.flavor == 0 and \
       graph.framework not in {"ccd", "dm", "pas", "psd", "ud"} or \
       graph.flavor == 1 and graph.framework not in {"eds", "ptg", "ucca"} or \
       graph.flavor == 2 and graph.framework not in {"amr", "drg"}:
    n += 1;
    report(graph,
           "invalid Flavor ({}) framework: ‘{}’"
           "".format(graph.flavor, graph.framework), stream = stream);

  if "input" in actions:
    if not isinstance(graph.input, str) or len(graph.input) == 0:
      n += 1;
      report(graph,
             "missing or invalid ‘input’ property",
             stream = stream);

  l = len(graph.input) if graph.input else 0;
  for node in graph.nodes:
    if not isinstance(node.id, int):
      n += 1;
      report(graph,
             "invalid identifier",
             node = node, stream = stream);
    if "anchors" in actions and node.anchors and l:
      for anchor in node.anchors:
        if anchor["from"] < 0 or anchor["from"] > l \
           or anchor["to"] < 0 or anchor["to"] > l \
           or anchor["from"] > anchor["to"]:
          n += 1;
          report(graph,
                 "invalid anchor: {}".format(anchor),
                 node = node, stream = stream);
          
  if "edges" in actions:
    #
    # the following is most likely redundant: the MRP input codec already has
    # to make sure all source and target identifiers actually exist.  maybe
    # add a type check (int), though?
    #
    nodes = {node.id: node for node in graph.nodes};
    for edge in graph.edges:
      if not isinstance(edge.src, int) or edge.src not in nodes:
        n += 1;
        report(graph,
               "invalid source",
               edge = edge, stream = stream);
      if not isinstance(edge.tgt, int) or edge.tgt not in nodes:
        n += 1;
        report(graph,
               "invalid target",
               edge = edge, stream = stream);
      num_attrib = len(edge.attributes) if edge.attributes else 0;
      num_values = len(edge.values) if edge.values else 0;
      if num_attrib != num_values:
        n += 1;
        report(graph,
               "unaligned ‘attributes’ vs. ‘values’",
               edge = edge, stream = stream);

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
