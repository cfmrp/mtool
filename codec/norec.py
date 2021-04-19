import json;
import operator;
import os;
import sys;

from graph import Graph

def read(fp, text = None, robust = False):
  def anchor(node):
    anchors = list();
    for string in node[1]:
      string = string.split(":");
      anchors.append({"from": string[0], "to": string[1]});
    return anchors;
  
  input, i = None, 0;
  for j, line in enumerate(fp):
    try:
      native = json.loads(line.rstrip());
      graph = Graph(native["sent_id"],  flavor = 1, framework = "norec");
      graph.add_input(native["text"]);
      for opinion in native["opinions"]:
        expression = opinion["Polar_expression"];
        expression = graph.add_node(label = "expression", anchors = anchor(expression));
        source = opinion["Source"];
        if len(source[1]):
          source = graph.add_node(label = "source", anchors = anchor(source));
          graph.add_edge(expression.id, source.id, None);
        target = opinion["Target"];
        if len(target[1]):
          target = graph.add_node(label = "target", anchors = anchor(target));
          graph.add_edge(expression.id, target.id, opinion["Polarity"]);
      yield graph, None;
    except Exception as error:
      print("codec.norec.read(): ignoring line {}: {}"
            "".format(j, error), file = sys.stderr);
