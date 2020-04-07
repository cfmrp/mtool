from operator import itemgetter;
import os.path;
import re;
import xml.etree.ElementTree as ET;

from graph import Graph;

def walk(id, node, parent, nodes, edges, ns):
  i = node.get("id");
  o = node.findtext(ns + "ord");
  if i is None or o is None and parent is not None:
    raise Exception("treex.walk(): "
                    "missing ‘id’ or ‘ord’ values while decoding tree #{}; exit."
                    "".format(id));
#  print(i, o, node.findtext(ns + "t_lemma"));
  nodes.append((i, int(o) if o is not None else 0, node));

  if edges is not None:
    functor = node.findtext(ns + "functor");
    if parent is not None and functor is not None:
      edges.append((parent, i, functor));

  children = node.find(ns + "children");
  if children is not None:
    for child in children:
      if child.tag == ns + "LM":
        walk(id, child, i, nodes, edges, ns);
    if children.find(ns + "LM") is None:
      walk(id, children, i, nodes, edges, ns);

def read(fp, text = None):
  ns = "{http://ufal.mff.cuni.cz/pdt/pml/}";

  #
  # _fix_me_
  # factor out the anchor()ing code into a reusable form.        (oe; 4-apr-20)
  #
  n = None;
  i = 0;

  def skip():
    nonlocal i;
    while i < n and graph.input[i] in {" ", "\t"}:
      i += 1;

  def scan(candidates):
    for candidate in candidates:
      if graph.input.startswith(candidate, i):
        return len(candidate);

  def anchor(form):
    nonlocal i;
    skip();
    m = None;
    if graph.input.startswith(form, i):
      m = len(form);
    else:
      for old, new in {("‘", "`"), ("’", "'")}:
        form = form.replace(old, new);
        if graph.input.startswith(form, i):
          m = len(form);
          break;
      if not m:
        m = scan({"“", "\"", "``"}) or scan({"‘", "`"}) \
            or scan({"”", "\"", "''"}) or scan({"’", "'"}) \
            or scan({"—", "—", "---", "--"}) \
            or scan({"…", "...", ". . ."});
    if m:
      anchor = {"from": i, "to": i + m};
      i += m;
      skip();
      return anchor;
    else:
      raise Exception("{}: failed to anchor |{}| in |{}| ({})"
                      "".format(graph.id, form, graph.input, i));

  tree = ET.parse(fp).getroot();
  bundles = tree.find(ns + "bundles");
  for item in bundles.findall(ns + "LM"):
    id = item.get("id");
    graph = Graph(id, flavor = 0, framework = "ptg");
    surface = list(); nodes = list(); edges = list();
    for zone in item.iter(ns + "zone"):
      if zone.get("language") == "en":
        sentence = zone.findtext(ns + "sentence");
        trees = zone.find(ns + "trees");
        if trees is not None:
          atree = trees.find(ns + "a_tree");
          ttree = trees.find(ns + "t_tree");
          root = atree.find(ns + "children");
          top = ttree.find(ns + "children");
#          print(id, sentence, atree, ttree, root, top);
          if root is None or top is None:
            raise Exception("treex.read(): "
                            "missing ‘a_tree’ or ‘t_tree’ values while decoding tree #{}; exit."
                            "".format(id));
          walk(id, root, None, surface, None, ns);
          walk(id, top, None, nodes, edges, ns);
    #
    # determine character-based anchors for all .surface. (analytical) tokens
    #
    anchoring = dict();
    if sentence is not None:
      graph.add_input(sentence);
      n = len(graph.input);
      i = 0;
      for node in sorted(surface, key = itemgetter(1)):
        anchoring[node[0]] = anchor(node[2].findtext(ns + "form"));

    #
    # now process tectogrammatical nodes in surface order (as indicated in the
    # annotations): map to consecutive numerical identifiers; retrieve anchors
    # from corresponding analytical nodes; and create actual (new) graph nodes.
    #
    mapping = {};
    to = 0;
    for node in sorted(nodes, key = itemgetter(1)):
      mapping[node[0]] = i = len(mapping);
      properties = dict();

      a = node[2].find(ns + "a");
      if a is not None:
        anchors = list();
        for lex in a:
          if len(lex) == 0:
            anchors.append(anchoring[lex.text]);
          else:
            for lm in lex.findall(ns + "LM"):
              anchors.append(anchoring[lm.text]);
        anchors = sorted(anchors, key = itemgetter("to"));
        to = anchors[-1]["to"];
      else:
        #
        # _fix_me_
        # discuss anchoring of generated nodes: currently, for uniformity, we
        # anchor them to an empty string immediately after the final character
        # of the preceding non-generated node.  but this arguably introduces a
        # vacuous piece of information, unless one were to argue that it rather
        # is an encoding of the node status for generated nodes? (oe; 4-apr-20)
        #
        anchors = [{"from": to, "to": to}];

      #
      # the node label comes from the tectogrammatical lemma
      #
      lemma = node[2].findtext(ns + "t_lemma");

      frame = node[2].findtext(ns + "val_frame.rf");
      #
      # where present (mostly on verbs), extract the valency frame identifier
      # _fix_me_
      # for compatibility with earlier PSD releases, strip prefix that seems to
      # identify the valency dictionary.                         (oe; 4-apr-20) 
      #
      if frame is not None:
        if "#" in frame:
          properties["frame"] = frame[frame.index("#") + 1:];
        else:
          properties["frame"] = frame;

      #
      # selectively expose grammatemes as node-local properties, but ignore
      # (vanilla but very high-frequent) default values
      #
      grammatemes = node[2].find(ns + "gram");
      if grammatemes is not None:
        for property, default in [("tense", {"nil"}), ("negation", {"neg0"})]:
          match = grammatemes.findtext(ns + property);
          if match is not None and match not in default:
            properties[property] = match;

      graph.add_node(id = i, label = lemma, anchors = anchors,
                     properties = properties.keys(),
                     values = properties.values(),
                     top = node[0] == top.get("id"));

    #
    # similarly, record all edges, now using mapped identifiers
    #
    for source, target, label in edges:
      graph.add_edge(mapping[source], mapping[target], label);

    #
    # in a second pass (so that all internal identifiers are mapped already),
    # create edges reflecting coreference annotations.
    #
    for node in nodes:
      coref = node[2].findtext(ns + "coref_gram.rf");
      if coref is not None:
        graph.add_edge(mapping[node[0]], mapping[coref], "coref_gram");

    yield graph, None;
