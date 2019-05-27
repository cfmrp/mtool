from score.core import fscore;
from smatch.smatch import get_amr_match;

def tuples(graph, prefix):
  #
  # mimicry of get_triples() in amr.py
  #  
  map = dict();
  instances = [];
  relations = [];
  attributes = [];
  for node in graph.nodes:
    map[node.id] = name = prefix + str(node.id);
    instances.append(("instance", name, node.label));
    if node.is_top:
      attributes.append(("TOP", name, node.label));
    if node.properties and node.values:
      for property, value in zip(node.properties, node.values):
        attributes.append((property, name, value));
  for edge in graph.edges:
    relations.append((edge.lab, map[edge.src], map[edge.tgt]));
  return instances, attributes, relations;
        
def evaluate(golds, systems, stream, format = "json"):
  tg = ts = tc = 0;
  gprefix = "g"; sprefix = "s";
  for gold, system in zip(golds, systems):
    ginstances, gattributes, grelations = tuples(gold, gprefix);
    sinstances, sattributes, srelations = tuples(gold, sprefix);
    correct, system, gold \
      = get_amr_match(None, None, gold.id,
                      instance1 = ginstances, attributes1 = gattributes,
                      relation1 = grelations, prefix1 = gprefix,
                      instance2 = sinstances, attributes2 = sattributes,
                      relation2 = srelations, prefix2 = sprefix);
    tg += correct; ts += system; tc += correct;
  p, r, f = fscore(tg, ts, tc);
  result = {"p": p, "r": r, "f": f};
  print(result, file = stream);
