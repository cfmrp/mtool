import sys;

import score.core;
from smatch.smatch import get_amr_match;

def tuples(graph, prefix, values, faith = True):
  #
  # mimicry of get_triples() in amr.py
  #
  id = 0;
  mapping = dict();
  instances = [];
  relations = [];
  attributes = [];
  n = 0;
  for node in graph.nodes:
    mapping[node.id] = name = prefix + str(id);
    id += 1;
    if "anchors" in values and node.anchors is not None:
      anchor = score.core.anchor(node);
      if graph.input: anchor = score.core.explode(graph.input, anchor)
      attributes.append(("anchor", name, str(anchor)));
    if "labels" in values and node.label is not None:
      instance = node.label;
    else:
      instance = "__()_{}__".format(prefix, n);
      n += 1;
    instances.append(("instance", name, instance));
    if "tops" in values and node.is_top:
      #
      # the native SMATCH code (wrongly, i believe) ties the top property to
      # the node label (see https://github.com/cfmrp/mtool/issues/12).  we get
      # to choose whether to faithfully replicate those scores or not.
      #
      attributes.append(("TOP", name,
                         node.label if node.label and faith else ""));
    if "properties" in values and node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        attributes.append((property, name, value));
  for edge in graph.edges:
    if "edges" in values:
      relations.append((edge.lab, mapping[edge.src], mapping[edge.tgt]));
    if "attributes" in values:
      if edge.attributes and edge.values:
        for attribute, value in zip(edge.attributes, edge.values):
          relations.append((str((attribute, value)),
                            mapping[edge.src], mapping[edge.tgt]));
  return instances, attributes, relations, n;

def smatch(gold, system, limit = 20, values = {}, trace = 0, faith = True):
  gprefix = "g"; sprefix = "s";
  ginstances, gattributes, grelations, gn \
    = tuples(gold, gprefix, values, faith);
  sinstances, sattributes, srelations, sn \
    = tuples(system, sprefix, values, faith);
  if trace > 1:
    print("gold instances [{}]: {}\ngold attributes [{}]: {}\n"
          "gold relations [{}]: {}"
          "".format(len(ginstances), ginstances,
                    len(gattributes), gattributes,
                    len(grelations), grelations),
          file = sys.stderr);
    print("system instances [{}]: {}\nsystem attributes [{}]: {}\n"
          "system relations [{}]: {}"
          "".format(len(sinstances), sinstances,
                    len(sattributes), sattributes,
                    len(srelations), srelations),
          file = sys.stderr);
  correct, gold, system, mapping \
    = get_amr_match(None, None, gold.id, limit = limit,
                    instance1 = ginstances, attributes1 = gattributes,
                    relation1 = grelations, prefix1 = gprefix,
                    instance2 = sinstances, attributes2 = sattributes,
                    relation2 = srelations, prefix2 = sprefix);
  return correct, gold - gn, system - sn, mapping;

def evaluate(golds, systems, format = "json", limit = 20,
             values = {}, trace = 0):
  if limit is None or not limit > 0: limit = 20;
  if trace > 1: print("RRHC limit: {}".format(limit), file = sys.stderr);
  tg = ts = tc = n = 0;
  scores = dict() if trace else None;
  for gold, system in score.core.intersect(golds, systems):
    id = gold.id;
    correct, gold, system, mapping \
      = smatch(gold, system, limit, values, trace);
    tg += gold; ts += system; tc += correct;
    n += 1;
    if trace:
      if id in scores:
        print("smatch.evaluate(): duplicate graph identifier: {}"
              "".format(id), file = sys.stderr);
      scores[id] = {"g": gold, "s": system, "c": correct};
      if trace > 1:
        p, r, f = score.core.fscore(gold, system, correct);
        print("G: {}; S: {}; C: {}; P: {}; R: {}; F: {}"
              "".format(gold, system, correct, p, r, f), file = sys.stderr);
    
  p, r, f = score.core.fscore(tg, ts, tc);
  result = {"n": n, "g": tg, "s": ts, "c": tc, "p": p, "r": r, "f": f};
  if trace: result["scores"] = scores;
  return result;
