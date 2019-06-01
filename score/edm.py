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
    if node.label is not None: names.add((identity, node.label));
    if node.is_top: tops.add(identity);
    if node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        properties.add((identity, property, value))
  for edge in graph.edges:
    arguments.add((identities[edge.src], identities[edge.tgt], edge.lab));
  return names, arguments, properties, tops;

def evaluate(golds, systems, stream, format = "json", trace = False):
  tgn = tsn = tcn = 0;
  tga = tsa = tca = 0;
  tgt = tst = tct = 0;
  tgp = tsp = tcp = 0;
  scores = [];
  result = {"n": 0};
  for gold, system in intersect(golds, systems):
    gnames, garguments, gproperties, gtops = tuples(gold);
    snames, sarguments, sproperties, stops = tuples(system);
    if trace:
      print("[{}] gold:\n{}\n{}\n{}\n{}\n\n"
            "".format(gold.id, gtops, sorted(gnames, key = lambda foo: foo[0][0]), sorted(garguments, key = lambda foo: foo[0][0]), gproperties));
      print("[{}] system:\n{}\n{}\n{}\n{}\n\n"
            "".format(gold.id, stops, sorted(snames, key = lambda foo: foo[0][0]), sorted(sarguments, key = lambda foo: foo[0][0]), sproperties));
    gn = len(gnames); sn = len(snames);
    cn = len(gnames & snames);
    ga = len(garguments); sa = len(sarguments);
    ca = len(garguments & sarguments);
    gt = len(gtops); st = len(stops);
    ct = len(gtops & stops);
    gp = len(gproperties); sp = len(sproperties);
    cp = len(gproperties & sproperties);
    tgn += gn; tsn += sn; tcn += cn;
    tga += ga; tsa += sa; tca += ca;
    tgt += gt; tst += st; tct += ct;
    tgp += gp; tsp += sp; tcp += cp;
    result["n"] += 1;
  p, r, f = fscore(tgn, tsn, tcn);
  result["names"] = {"g": tgn, "s": tsn, "c": tcn, "p": p, "r": r, "f": f};
  p, r, f = fscore(tga, tsa, tca);
  result["arguments"] = {"g": tga, "s": tsa, "c": tca, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgt, tst, tct);
  result["tops"] = {"g": tgt, "s": tst, "c": tct, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgp, tsp, tcp);
  result["properties"] = {"g": tgp, "s": tsp, "c": tcp, "p": p, "r": r, "f": f};
  print(result, file = stream);
