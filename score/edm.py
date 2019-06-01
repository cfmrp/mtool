from graph import Graph;
from score.core import anchor, fscore, intersect;

def tuples(graph):
  identities = dict();
  names = set();
  tops = set();
  arguments = set();
  properties = set();
  for node in graph.nodes:
    identity = tuple(anchor(node));
    identities[node.id] = identity;
    if node.label is not None: names.add(node.label);
    if node.is_top: tops.add(identity);
    if node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        properties.add((identity, property, value))
  for edge in graph.edges:
    arguments.add((identities[edge.src], identities[edge.tgt], edge.lab));
  return names, arguments, properties, tops;

def evaluate(golds, systems, stream, format = "json", trace = False):
  tgn = tsn = tmn = 0;
  tga = tsa = tma = 0;
  tgt = tst = tmt = 0;
  tgp = tsp = tmp = 0;
  scores = [];
  result = {"n": 0};
  for gold, system in intersect(golds, systems):
    gnames, garguments, gproperties, gtops = tuples(gold);
    snames, sarguments, sproperties, stops = tuples(system);
    gn = len(gnames); sn = len(snames);
    mn = len(gnames & snames);
    ga = len(garguments); sa = len(sarguments);
    ma = len(garguments & sarguments);
    gt = len(gtops); st = len(stops);
    mt = len(gtops & stops);
    gp = len(gproperties); sp = len(sproperties);
    mp = len(gproperties & sproperties);
    tgn += gn; tsn += sn; tmn += mn;
    tga += ga; tsa += sa; tma += ma;
    tgt += gt; tst += st; tmt += mt;
    tgp += gp; tsp += sp; tmp += mp;
    result["n"] += 1;
  p, r, f = fscore(tgn, tsn, tmn);
  result["names"] = {"g": tgn, "s": tsn, "m": tmn, "p": p, "r": r, "f": f};
  p, r, f = fscore(tga, tsa, tma);
  result["arguments"] = {"g": tga, "s": tsa, "m": tma, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgt, tst, tmt);
  result["tops"] = {"g": tgt, "s": tst, "m": tmt, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgp, tsp, tmp);
  result["properties"] = {"g": tgp, "s": tsp, "m": tmp, "p": p, "r": r, "f": f};
  print(result, file = stream);
