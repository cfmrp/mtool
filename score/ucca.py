import sys
from operator import itemgetter;

from score.core import anchor, explode, intersect, fscore;


def identify(graph, node, anchors = None, dominated = None, recursion = False):
  #
  # from how this ends up being called in various places, there is a missing
  # higher-level interface; something like (maybe even as a Graph method):
  #
  # identities = identify(graph, walk = True, explode = True)
  #
  if dominated is None:
    dominated = dict()
  if node not in dominated: dominated[node] = node_dominated = set()
  else: node_dominated = dominated[node]
  if anchors is None:
    anchors = dict();
  elif node in anchors:
    return anchors, dominated;
  anchors[node] = node_anchors = anchor(graph.find_node(node));
  for edge in graph.edges:
    if edge.attributes is None or "remote" not in edge.attributes:
      if node == edge.src:
        identify(graph, edge.tgt, anchors, dominated, True);
        for leaf in anchors[edge.tgt]:
          if leaf not in node_anchors: node_anchors.append(leaf);
        node_dominated.add(edge.tgt)
        node_dominated |= dominated[edge.tgt]
  if not recursion:
      anchors = {key: tuple(sorted(value, key = itemgetter(0, 1)))
                 for key, value in anchors.items()}
  return anchors, dominated;

def tuples(graph):
  identities = dict();
  for node in graph.nodes:
    identities, _ = identify(graph, node.id, identities);
  #
  # for robust comparison, represent each yield as a character set
  #
  if graph.input:
    for id in identities:
      identities[id] = explode(graph.input, identities[id]);
  lprimary = set();
  lremote = set();
  uprimary = set();
  uremote = set();
  for edge in graph.edges:
    source = identities[edge.src];
    target = identities[edge.tgt];
    if edge.attributes and "remote" in edge.attributes:
      lremote.add((source, target, edge.lab));
      uremote.add((source, target));
    else:
      lprimary.add((source, target, edge.lab));
      uprimary.add((source, target));
  return lprimary, lremote, uprimary, uremote;

def evaluate(golds, systems, format = "json", trace = 0):
  tglp = tslp = tclp = 0;
  tgup = tsup = tcup = 0;
  tglr = tslr = tclr = 0;
  tgur = tsur = tcur = 0;
  tp = tr = 0;
  scores = dict() if trace else None;
  result = {"n": 0, "labeled": dict(), "unlabeled": dict()};

  for gold, system in intersect(golds, systems):
    glprimary, glremote, guprimary, guremote = tuples(gold);
    slprimary, slremote, suprimary, suremote = tuples(system);
    glp = len(glprimary); slp = len(slprimary);
    clp = len(glprimary & slprimary);
    gup = len(guprimary); sup = len(suprimary);
    cup = len(guprimary & suprimary);
    glr = len(glremote); slr = len(slremote);
    clr = len(glremote & slremote);
    gur = len(guremote); sur = len(suremote);
    cur = len(guremote & suremote);
    tglp += glp; tslp += slp; tclp += clp;
    tgup += gup; tsup += sup; tcup += cup;
    tglr += glr; tslr += slr; tclr += clr;
    tgur += gur; tsur += sur; tcur += cur;
    result["n"] += 1;
    if trace:
      if gold.id in scores:
        print("ucca.evaluate(): duplicate graph identifier: {}"
              "".format(gold.id), file = sys.stderr);
      score = {"labeled": dict(), "unlabeled": dict()};
      score["labeled"]["primary"] = {"g": glp, "s": slp, "c": clp};
      score["labeled"]["remote"] = {"g": glr, "s": slr, "c": clr};
      score["unlabeled"]["primary"] = {"g": gup, "s": sup, "c": cup};
      score["unlabeled"]["remote"] = {"g": gur, "s": sur, "c": cur};
      scores[gold.id] = score;
      if trace > 1: print("{}: {}".format(gold.id, score));
  p, r, f = fscore(tglp, tslp, tclp);
  result["labeled"]["primary"] = \
    {"g": tglp, "s": tslp, "c": tclp, "p": p, "r": r, "f": f};
  p, r, f = fscore(tglr, tslr, tclr);
  result["labeled"]["remote"] = \
    {"g": tglr, "s": tslr, "c": tclr, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgup, tsup, tcup);
  result["unlabeled"]["primary"] = \
    {"g": tgup, "s": tsup, "c": tcup, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgur, tsur, tcur);
  result["unlabeled"]["remote"] = \
    {"g": tgur, "s": tsur, "c": tcur, "p": p, "r": r, "f": f};
  if trace: result["scores"] = scores;
  return result;
