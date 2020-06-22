import json;
import operator;
import os;
import sys;

from graph import Graph

def read(fp, text = None, robust = False):
  input, i = None, 0;
  def compute(form):
    nonlocal i;
    m = None;
    j = input.find(form, i);
    if j >= i:
      i, m = j, len(form);
    else:
      base = form;
      k, l = len(input), 0;
      for old, new in {("‘", "`"), ("‘", "'"), ("’", "'"), ("`", "'"),
                       ("“", "\""), ("”", "\""),
                       ("–", "--"), ("–", "---"), ("—", "---"),
                       ("…", "..."), ("…", ". . .")}:
        form = base.replace(old, new);
        j = input.find(form, i);
        if j >= i and j < k: k, l = j, len(form);
      if k < len(input): i, m = k, l;
    if m:
      match = {"from": i, "to": i + m}; 
      i += m;
      return match;
    else:
      raise Exception("failed to anchor |{}| in |{}|{}| ({})"
                      "".format(form, input[:i], input[i:], i));

  def anchor(graph, old, new):
    nonlocal input, i;
    strings = dict();
    for node in graph.nodes:
      for j in range(len(node.anchors) if node.anchors else 0):
        start, end = node.anchors[j]["from"], node.anchors[j]["to"];
        strings[(start, end)] = old[start:end];
    input, i = new, 0;
    for key in sorted(strings.keys(), key = operator.itemgetter(0, 1)):
      strings[key] = compute(strings[key]);
    for node in graph.nodes:
      for j in range(len(node.anchors) if node.anchors else 0):
        node.anchors[j] \
          = strings[(node.anchors[j]["from"], node.anchors[j]["to"])];

  for j, line in enumerate(fp):
    try:
      graph = Graph.decode(json.loads(line.rstrip()), robust = robust);
      if text is not None:
        old = graph.input;
        graph.add_input(text);
        anchor(graph, old, graph.input);
      yield graph, None;
    except Exception as error:
      print("codec.mrp.read(): ignoring line {}: {}"
            "".format(j, error), file = sys.stderr);
