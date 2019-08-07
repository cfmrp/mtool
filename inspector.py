import sys;

from graph import Graph;

def summarize(graphs, golds):
  ids = None;
  if golds is not None:
    ids = {"dm": set(), "psd": set(),
           "eds": set(), "ucca": set(),
           "amr": set()};
    for gold in golds:
      targets = gold.targets();
      if targets is None: targets = [gold.framework];
      for target in targets:
        ids[target].add(gold.id);
  counts = {"dm": 0, "psd": 0, "eds": 0, "ucca": 0, "amr": 0};
  for graph in graphs:
    framework = graph.framework;
    if golds is None or graph.id in ids[framework]:
      counts[framework] += 1;
  complete = True;
  for key in ["dm", "psd", "eds", "ucca", "amr"]:
    if len(ids[key]) != counts[key]: complete = False;
  counts["complete"] = complete;
  return counts;
