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
    #
    # _fix_me_
    # do something about tops: maybe a fourth sub-metric?
    #
    if node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        properties.add((anchor, property, value))
  for edge in graph.edges:
    arguments.add((map[edge.src], map[edge.tgt], edge.lab));
  return names, arguments, properties;

def evaluate(golds, systems, stream, format = "json", trace = False):
  tgn = tsn = tmn = 0;
  tga = tsa = tma = 0;
  tgp = tsp = tmp = 0;
  scores = [];
  result = {"n": 0};
  for gold, system in zip(golds, systems):
    gnames, garguments, gproperties = tuples(gold);
    snames, sarguments, sproperties = tuples(system);
    gn = len(gnames); sn = len(snames);
    mn = len(gnames & snames);
    ga = len(garguments); sa = len(sarguments);
    ma = len(garguments & sarguments);
    gp = len(gproperties); sp = len(sproperties);
    mp = len(gproperties & sproperties);
    tgn += gn; tsn += sn; tmn += mn;
    tga += ga; tsa += sa; tma += ma;
    tgp += gp; tsp += sp; tmp += mp;
    result["n"] += 1;
  p, r, f = fscore(tgn, tsn, tmn);
  result["names"] = {"g": tgn, "s": tsn, "m": tmn, "p": p, "r": r, "f": f};
  p, r, f = fscore(tga, tsa, tma);
  result["arguments"] = {"g": tga, "s": tsa, "m": tma, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgp, tsp, tmp);
  result["properties"] = {"g": tgp, "s": tsp, "m": tmp, "p": p, "r": r, "f": f};
  print(result, file = stream);
