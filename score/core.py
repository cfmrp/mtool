from operator import itemgetter;

from graph import Graph;

def intersect(golds, systems):
  gold = {graph.id: graph for graph in golds};
  system = {graph.id: graph for graph in systems};
  for key in sorted(gold.keys() & system.keys()):
    yield gold[key], system[key];

def anchor(node):
  result = list();
  if node.anchors is not None:
    for span in node.anchors:
      if "from" in span and "to" in span:
        result.append((span["from"], span["to"]));
  return result;

def fscore(gold, system, correct):
  p = correct / system if system else 0.0;
  r = correct / gold if gold else 0.0;
  f = 2 * p * r / (p + r) if p + r != 0 else 0.0;
  return p, r, f;
    
      
