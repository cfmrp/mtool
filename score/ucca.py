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
    if edge.properties and "remote" in edge.properties:
      lremote.add((source, target, edge.lab));
      uremote.add((source, target));
    else:
      lprimary.add((source, target, edge.lab));
      uprimary.add((source, target));
  return lprimary, lremote, uprimary, uremote;

def evaluate(golds, systems, stream, format = "json", trace = False):
  tglp = tslp = tclp = 0;
  tgup = tsup = tcup = 0;
  tglr = tslr = tclr = 0;
  tgur = tsur = tcur = 0;
  tp = tr = 0;
  scores = [];
  result = {"n": 0};

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

  result["labeled"] = dict();
  result["unlabeled"] = dict();
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
  print(result, file = stream);
