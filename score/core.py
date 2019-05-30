from graph import Graph;
from operator import itemgetter;

def intersect(golds, systems):
  gold = {graph.id: graph for graph in golds};
  system = {graph.id: graph for graph in systems};
  for key in gold.keys() & system.keys():
    yield gold[key], system[key];

def anchor(node):
  result = list();
  if node.anchors is not None:
    for span in node.anchors:
      if "from" in span and "to" in span:
        result.append((span["from"], span["to"]));
  return result;

def identify(graph, node, mapping = None, recursion = False):
  if mapping is None: mapping = dict();
  if node in mapping:
    return mapping;
  mapping[node] = anchor(graph.find_node(node));
  for edge in graph.edges:
    if edge.properties is not None and "remote" not in edge.properties:
      if node == edge.src:
        identify(graph, edge.tgt, mapping, True);
        for leaf in mapping[edge.tgt]:
          if leaf not in mapping[node]: mapping[node].append(leaf);
  if not recursion:
    for key in mapping:
      mapping[key] = tuple(sorted(mapping[key], key = itemgetter(0, 1)));
  return mapping;

def fscore(gold, system, correct):
  p = correct / system if system else 0.0;
  r = correct / gold if gold else 0.0;
  f = 2 * p * r / (p + r) if p + r != 0 else 0.0;
  return p, r, f;
