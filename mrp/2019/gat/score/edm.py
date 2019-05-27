from graph import Graph;
from score.core import fscore;

def tuples(graph):
  map = dict();
  names = set();
  arguments = set();
  properties = set();
  for node in graph.nodes:
    anchor = node.anchors[0] if node.anchors else None;
    if anchor and "from" in anchor and "to" in anchor:
      anchor = (anchor["from"], anchor["to"]);
    map[node.id] = anchor;
    names.add(node.label);
    if node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        properties.add((anchor, property, value))
  for edge in graph.edges:
    arguments.add((map[edge.src], map[edge.tgt], edge.lab));
  return names, arguments, properties;

def evaluate(golds, systems, stream, format = "json", trace = False):
  tgn = tsn = tcn = 0;
  tga = tsa = tca = 0;
  tgp = tsp = tcp = 0;
  scores = [];
  for gold, system in zip(golds, systems):
    gnames, garguments, gproperties = tuples(gold);
    snames, sarguments, sproperties = tuples(system);
    gn = len(gnames); sn = len(snames);
    cn = len(gnames & snames);
    ga = len(garguments); sa = len(sarguments);
    ca = len(garguments & sarguments);
    gp = len(gproperties); sp = len(sproperties);
    cp = len(gproperties & sproperties);
    tgn += gn; tsn += sn; tcn += cn;
    tga += ga; tsa += sa; tca += ca;
    tgp += gp; tsp += sp; tcp += cp;
  result = {};
  p, r, f = fscore(tgn, tsn, tcn);
  result["names"] = {"p": p, "r": r, "f": f};
  p, r, f = fscore(tga, tsa, tca);
  result["arguments"] = {"p": p, "r": r, "f": f};
  p, r, f = fscore(tgp, tsp, tcp);
  result["properties"] = {"p": p, "r": r, "f": f};
  print(result, file = stream);
