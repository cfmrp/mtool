import sys;

#
# _fix_me_
# maybe use Unicode character classes instead, even if it likely would mean
# many calls to match one-character regular expressions?
#
PUNCTUATION = frozenset(".?!;,:“\"”‘'’()[]{} \t\n\f")
SPACE = frozenset(" \t\n\f")

def intersect(golds, systems, quiet = False):
  golds = {(graph.framework, graph.id): graph for graph in golds}
  seen = set()
  for graph in systems:
    key = (graph.framework, graph.id)
    if key in seen:
      if not quiet:
        print("score.intersect(): ignoring duplicate {} graph #{}"
              .format(graph.framework, graph.id), file=sys.stderr);
    else:
      seen.add(key)
      gold = golds.get(key)
      if gold is None:
        if not quiet:
          print("score.intersect(): ignoring {} graph #{} with no gold graph"
                .format(graph.framework, graph.id), file=sys.stderr)
      else:
        yield gold, graph

  for key in golds.keys() - seen:
    gold = golds[key]
    if not quiet:
      print("score.intersect(): missing system {} graph #{}"
            .format(gold.framework, gold.id), file=sys.stderr);
    #
    # manufacture an empty graph as the system graph
    #
    from graph import Graph;
    yield gold, Graph(gold.id, flavor = gold.flavor, framework = gold.framework);

def anchor(node):
  result = list();
  if node.anchors is not None:
    for span in node.anchors:
      if "from" in span and "to" in span:
        result.append((span["from"], span["to"]));
  return result;

def explode(string, anchors, trim = PUNCTUATION):
  result = set();
  for anchor in anchors:
    start = end = None;
    if isinstance(anchor, tuple):
      start, end = anchor;
    elif "from" in anchor and "to" in anchor:
      start = anchor["from"]; end = anchor["to"];
    if start is not None and end is not None:
      while start < end and string[start] in trim:
        start += 1;
      while end > start and string[end - 1] in trim:
        end -= 1;
      for i in range(start, end):
        if string[i] not in SPACE:
          result.add(i);
  return frozenset(result);

def fscore(gold, system, correct):
  p = correct / system if system else 0.0;
  r = correct / gold if gold else 0.0;
  f = 2 * p * r / (p + r) if p + r != 0 else 0.0;
  return p, r, f;
    
      
