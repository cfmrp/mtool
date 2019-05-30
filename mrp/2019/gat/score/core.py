from graph import Graph;
from operator import itemgetter;

def intersect(golds, systems):
  gold = {graph.id: graph for graph in golds};
  system = {graph.id: graph for graph in systems};
  for key in gold.keys() & system.keys():
    yield gold[key], system[key];

def anchor(node):
  result = list();
  if node.anchors != None:
    for anchor in node.anchors:
      if anchor and "from" in anchor and "to" in anchor:
        result.append((anchor["from"], anchor["to"]));
  return result;

def identify(graph, node, map = dict(), recursion = False):
  if node in map:
    return map;
  map[node] = anchor(graph.find_node(node));
  for edge in graph.edges:
    if edge.properties != None and "remote" not in edge.properties:
      if node == edge.src:
        identify(graph, edge.tgt, map, True);
        for leaf in map[edge.tgt]:
          if leaf not in map[node]: map[node].append(leaf);
  if not recursion:
    for key in map:
      map[key] = tuple(sorted(map[key], key = itemgetter(0, 1)));
  return map;

def fscore(gold, system, correct):
  p = correct / system if system else 0.0;
  r = correct / gold if gold else 0.0;
  f = 2 * p * r / (p + r) if p + r != 0 else 0.0;
  return p, r, f;
