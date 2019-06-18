from score.core import identify, intersect, fscore;

def tuples(graph):
  identities = dict();
  for node in graph.nodes:
    identities = identify(graph, node.id, identities);
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
