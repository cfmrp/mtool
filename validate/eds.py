import sys;

from graph import Graph;
from validate.utilities import report;

def test(graph, actions, stream = sys.stderr):
  n = 0;
  for node in graph.nodes:
    if not isinstance(node.label, str) or len(node.label) == 0:
      n += 1;
      report(graph,
             "missing or invalid label",
             node = node, framework = "EDS", stream = stream);
    message = None;
    if "anchors" in actions:
      if not isinstance(node.anchors, list):
        message = "missing or invalid anchoring";
      elif len(node.anchors) != 1 \
        or ("from" not in node.anchors[0] or "to" not in node.anchors[0]):
        message = "invalid ‘anchors’ value: {}".format(node.anchors);
    if message is not None:
      n += 1;
      report(graph, message,
             node = node, framework = "EDS", stream = stream);
  return n;

