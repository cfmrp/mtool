from graph import Graph;
from score.core import identify, intersect, fscore;

def tuples(graph):
  map = dict();
  for node in graph.nodes:
    map = identify(graph, node.id, map);
  lprimary = set();
  lremote = set();
  uprimary = set();
  uremote = set();
  for edge in graph.edges:
    source = map[edge.src];
    target = map[edge.tgt];
    if edge.properties and "remote" in edge.properties:
      lremote.add((source, target, edge.lab));
      uremote.add((source, target));
    else:
      lprimary.add((source, target, edge.lab));
      uprimary.add((source, target));
  return lprimary, lremote, uprimary, uremote;

def evaluate(golds, systems, stream, format = "json", trace = False):
  tglp = tslp = tmlp = 0;
  tgup = tsup = tmup = 0;
  tglr = tslr = tmlr = 0;
  tgur = tsur = tmur = 0;
  tp = tr = 0;
  scores = [];
  result = {"n": 0};

  for gold, system in intersect(golds, systems):
    glprimary, glremote, guprimary, guremote = tuples(gold);
    slprimary, slremote, suprimary, suremote = tuples(system);
    glp = len(glprimary); slp = len(slprimary);
    mlp = len(glprimary & slprimary);
    gup = len(guprimary); sup = len(suprimary);
    mup = len(guprimary & suprimary);
    glr = len(glremote); slr = len(slremote);
    mlr = len(glremote & slremote);
    gur = len(guremote); sur = len(suremote);
    mur = len(guremote & suremote);
    tglp += glp; tslp += slp; tmlp += mlp;
    tgup += gup; tsup += sup; tmup += mup;
    tglr += glr; tslr += slr; tmlr += mlr;
    tgur += gur; tsur += sur; tmur += mur;
    result["n"] += 1;

  result["labeled"] = dict();
  result["unlabeled"] = dict();
  p, r, f = fscore(tglp, tslp, tmlp);
  result["labeled"]["primary"] = \
    {"g": tglp, "s": tslp, "m": tmlp, "p": p, "r": r, "f": f};
  p, r, f = fscore(tglr, tslr, tmlr);
  result["labeled"]["remote"] = \
    {"g": tglr, "s": tslr, "m": tmlr, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgup, tsup, tmup);
  result["unlabeled"]["primary"] = \
    {"g": tgup, "s": tsup, "m": tmup, "p": p, "r": r, "f": f};
  p, r, f = fscore(tgur, tsur, tmur);
  result["unlabeled"]["remote"] = \
    {"g": tgur, "s": tsur, "m": tmur, "p": p, "r": r, "f": f};
  print(result, file = stream);
