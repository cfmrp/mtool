import sys;

from graph import Graph;

def summarize(graphs, golds):
  ids = None;
  if golds is not None:
    ids = dict();
    for gold in golds:
      language = gold.language();
      if language not in ids: ids[language] = dict();
      targets = gold.targets();
      if targets is None: targets = [gold.framework];
      for target in targets:
        if target not in ids[language]: ids[language][target] = set();
        ids[language][target].add(gold.id);

  counts = dict();
  seen = dict();
  targets = dict();
  targets["eng"] = ["eds", "ptg", "ucca", "amr", "drg"];
  targets["ces"] = ["ptg"];
  targets["deu"] = ["ucca", "drg"];
  targets["zho"] = ["amr"];
  for language in ["eng", "ces", "deu", "zho"]:
    counts[language] = dict();
    seen[language] = dict();
    for key in targets[language]:
      counts[language][key] = 0;
      seen[language][key] = set();

  for graph in graphs:
    language = graph.language();
    if language is None: language = "eng";
    framework = graph.framework;
    if golds is None or \
       language in ids and framework in ids[language] and \
       graph.id in ids[language][framework]:
      counts[language][framework] += 1;
      if graph.id in seen[language][framework]:
        print("inspector.summarize(): ignoring duplicate {} {} graph #{}."
              "".format(language, framework, graph.id),
              file = sys.stderr);
      else:
        seen[language][framework].add(graph.id);

  complete = True;
  for language in ["eng", "ces", "deu", "zho"]:
    for key in targets[language]:
      if len(ids[language][key]) != counts[language][key]: complete = False;
  counts["complete"] = complete;
  return counts;
