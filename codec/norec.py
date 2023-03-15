import json;
import operator;
import os;
import sys;

from graph import Graph;

def read(fp, text = None, reify = False, strict = False):
  def anchor(node):
    anchors = list();
    for string in node[1]:
      string = string.split(":");
      anchors.append({"from": int(string[0]), "to": int(string[1])});
    return anchors;

  for native in json.load(fp):
    map = dict();
    try:
      graph = Graph(native["sent_id"],  flavor = 1, framework = "norec");
      graph.add_input(native["text"]);
      if reify:
        top = graph.add_node(top = True);
      for opinion in native["opinions"]:
        expression = opinion["Polar_expression"];
        properties, values = list(), list();
        if not reify:
          properties = ["polarity"];
          values = [opinion["Polarity"]];
        expression = graph.add_node(label = "expression",
                                    top = not reify,
                                    properties = properties, values = values,
                                    anchors = anchor(expression));
        if reify:
          graph.add_edge(top.id, expression.id, opinion["Polarity"]);
        source = opinion["Source"];
        if len(source[1]):
          key = tuple(source[1]);
          if strict and key in map:
            source = map[key];
          else:
            source = graph.add_node(label = "source" if not strict else None,
                                    anchors = anchor(source));
            map[key] = source;
          graph.add_edge(expression.id, source.id, "source" if strict else None);
        target = opinion["Target"];
        if len(target[1]):
          key = tuple(target[1]);
          if strict and key in map:
            target = map[key];
          else:
            target = graph.add_node(label = "target" if not strict else None,
                                    anchors = anchor(target));
            map[key] = target;
          graph.add_edge(expression.id, target.id, "target" if strict else None);
      yield graph, None;
    except Exception as error:
      print("codec.norec.read(): ignoring {}: {}"
            "".format(native, error), file = sys.stderr);
