from operator import itemgetter;
import os.path;
import re;
import xml.etree.ElementTree as ET;

from graph import Graph;

referent_matcher = re.compile(r'^(b[0-9]+) REF ([estx][0-9]+) +% .* \[([0-9]+)\.\.\.([0-9]+)\]$');
concept_matcher = re.compile(r'^(b[0-9]+) ([^ ]+) ("[^ ]+") ([^ ]+) +% .* \[([0-9]+)\.\.\.([0-9]+)\]$');
role_matcher = re.compile(r'^(b[0-9]+) ([^ ]+) ([estx][0-9]+) ([^ ]+) +% .* \[([0-9]+)\.\.\.([0-9]+)\]$');
discourse_matcher = re.compile(r'^(b[0-9]+) ([^ ]+) (b[0-9]+) +% .* \[[0-9]+\.\.\.[0-9]+\]$');

def read(fp, text = None, reify = False):
  print(os.path.split(os.path.realpath(os.path.dirname(fp.name))));
  fp.readline().rstrip();
  fp.readline().rstrip();
  sentence = fp.readline()[5:-1];
  graph = Graph(42, flavor = 2, framework = "drg");
  mapping = dict();
  for line in fp:
    line = line.rstrip();
#    print(line);
    match = referent_matcher.match(line);
    if match is not None:
      box, referent, start, end = match.groups();
      if box not in mapping: mapping[box] = graph.add_node(type = 0);
      anchor = {"from": int(start), "to": int(end)};
      if referent not in mapping:
        mapping[referent] = graph.add_node(anchors = [anchor]);
      else:
        node = mapping[referent];
        node.add_anchor(anchor);
      graph.add_edge(mapping[box].id, mapping[referent].id, "in");
    else:
      match = concept_matcher.match(line);
      if match is not None:
        box, lemma, sense, referent, start, end = match.groups();
        anchor = {"from": int(start), "to": int(end)};
        if referent not in mapping:
          mapping[referent] = node = graph.add_node(anchors = [anchor]);
        else:
          node = mapping[referent];
          node.add_anchor(anchor);
        node.label = lemma;
        node.set_property("sense", sense);
      else:
        match = role_matcher.match(line);
        if match is not None:
          box, role, source, target, start, end = match.groups();
          if source not in mapping: mapping[source] = graph.add_node();
          if target[0] == "\"" and target[-1] == "\"":
            anchor = {"from": int(start), "to": int(end)};
            mapping[target] = graph.add_node(label = target, anchors = [anchor]);
          elif target not in mapping: mapping[target] = graph.add_node();
          graph.add_edge(mapping[source].id, mapping[target].id, role);
        else:
          match = discourse_matcher.match(line);
          if match is not None:
            top, relation, bottom = match.groups();
            if top not in mapping: mapping[top] = graph.add_node();
            if bottom not in mapping: mapping[bottom] = graph.add_node();
            graph.add_edge(mapping[top].id, mapping[bottom].id, relation);
          
  print(mapping)
  yield graph, None;
