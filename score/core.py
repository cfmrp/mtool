from operator import itemgetter;


#
# _fix_me_
# maybe use Unicode character classes instead, even if it likely would mean
# many calls to match one-character regular expressions?
#
PUNCTUATION = \
  {".", "?", "!", ";", ",", ":", "“", "\"", "”", "‘", "'", "’",
   "(", ")", "[", "]", "{", "}", " ", "\t", "\n", "\f"};
SPACE = {" ", "\t", "\n", "\f"};

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
    
      
