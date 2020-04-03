from operator import itemgetter;
import os.path;
import re;
import xml.etree.ElementTree as ET;

from graph import Graph;

def walk(id, node, parent, nodes, edges, ns):
  i = node.get("id");
  o = node.findtext(ns + "ord");
  if i is None or o is None and parent is not None:
    raise Exception("missing ‘id’ or ‘ord’ values while decoding tree #{}; exit."
                    "".format(id));
#  print(o, node.findtext(ns + "t_lemma"));
  nodes.append((i, int(o) if o is not None else 0, node));
  functor = node.findtext(ns + "functor");
  if parent is not None and functor is not None:
    edges.append((parent, i, functor));
  children = node.find(ns + "children");
  if children is not None:
    for child in children:
      if child.tag == ns + "LM":
        walk(id, child, i, nodes, edges, ns);

def read(fp, text = None):
  ns = "{http://ufal.mff.cuni.cz/pdt/pml/}";
  tree = ET.parse(fp).getroot();
  bundles = tree.find(ns + "bundles");
  item = bundles.find(ns + "LM");
  if item is not None:
      id = item.get("id");
      graph = Graph(id, flavor = 0, framework = "ptt");
      for zone in item.iter(ns + "zone"):
        if zone.get("language") == "en":
          sentence = zone.findtext(ns + "sentence");
          trees = zone.find(ns + "trees");
          if trees is not None:
            atree = trees.find(ns + "a_tree");
            ttree = trees.find(ns + "t_tree");
            print(id, sentence, ttree);
            root = ttree.find(ns + "children");
            if root is not None:
              nodes = list(); edges = list();
              walk(id, root, None, nodes, edges, ns);
      mapping = {};
      for node in sorted(nodes, key = itemgetter(1)):
        mapping[node[0]] = i = len(mapping);
        lemma = node[2].findtext(ns + "t_lemma");
        graph.add_node(id = i, label = lemma, top = node[2].tag == ns + "children");
#      print(len(nodes), nodes, edges);        
      for source, target, label in edges:
        graph.add_edge(mapping[source], mapping[target], label);
      yield graph, None;
