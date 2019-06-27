import sys;

from graph import Graph;
import score.core;

def tuples(graph, explode = False):
  identities = dict();
  names = set();
  tops = set();
  arguments = set();
  properties = set();
  for node in graph.nodes:
    if graph.input and explode:
      identity = score.core.explode(graph.input,
                                    score.core.anchor(node));
    else:
      identity = tuple(score.core.anchor(node));
    identities[node.id] = identity;
    if node.label is not None: names.add((identity, node.label));
    if node.is_top: tops.add(identity);
    if node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        properties.add((identity, property, value))
  for edge in graph.edges:
    arguments.add((identities[edge.src], identities[edge.tgt], edge.lab));
  return names, arguments, properties, tops;

def evaluate(golds, systems, format = "json", trace = 0):
  tgn = tsn = tcn = 0;
  tga = tsa = tca = 0;
  tgt = tst = tct = 0;
  tgp = tsp = tcp = 0;
  scores = dict() if trace else None;
  result = {"n": 0};
  for gold, system in score.core.intersect(golds, systems):
    explode = gold.input and system.input;
    gnames, garguments, gproperties, gtops = tuples(gold, explode = explode);
    snames, sarguments, sproperties, stops = tuples(system, explode = explode);
    if trace > 1:
      print("[{}] gold:\n{}\n{}\n{}\n{}\n\n"
            "".format(gold.id, gtops,
                      gnames, garguments, gproperties));
      print("[{}] system:\n{}\n{}\n{}\n{}\n\n"
            "".format(gold.id, stops,
                      snames, sarguments, sproperties));
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
    if trace:
      if gold.id in scores:
        print("edm.evaluate(): duplicate graph identifier: {}"
              "".format(gold.id), file = sys.stderr);
      scores[gold.id] = {"names": {"g": gn, "s": sn, "c": cn},
                         "arguments":  {"g": ga, "s": sa, "c": ca},
                         "tops": {"g": gt, "s": st, "c": ct},
                         "properties": {"g": gp, "s": sp, "c": cp}};
  if scores is not None: result["scores"] = scores;
  p, r, f = score.core.fscore(tgn, tsn, tcn);
  result["names"] = {"g": tgn, "s": tsn, "c": tcn, "p": p, "r": r, "f": f};
  p, r, f = score.core.fscore(tga, tsa, tca);
  result["arguments"] = {"g": tga, "s": tsa, "c": tca, "p": p, "r": r, "f": f};
  p, r, f = score.core.fscore(tgt, tst, tct);
  result["tops"] = {"g": tgt, "s": tst, "c": tct, "p": p, "r": r, "f": f};
  p, r, f = score.core.fscore(tgp, tsp, tcp);
  result["properties"] = {"g": tgp, "s": tsp, "c": tcp, "p": p, "r": r, "f": f};
  tga = tgn + tga + tgt + tgp;
  tsa = tsn + tsa + tst + tsp;
  tca = tcn + tca + tct + tcp;
  p, r, f = score.core.fscore(tga, tsa, tca);
  result["all"] = {"g": tga, "s": tsa, "c": tca, "p": p, "r": r, "f": f};
  return result;
