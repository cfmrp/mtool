# -*- coding: utf-8; -*-

# GraphaLogue Analyzer
# Marco Kuhlmann <marco.kuhlmann@liu.se>

import itertools
import statistics
import sys;

from treewidth import quickbb

class Node(object):

    def __init__(self, id, label = None, properties = None, anchors = None, top = False):
        self.id = id
        self.label = label;
        self.properties = properties;
        self.incoming_edges = set()
        self.outgoing_edges = set()
        self.anchors = anchors;
        self.is_top = top

    def is_root(self):
        return len(self.incoming_edges) == 0

    def is_leaf(self):
        return len(self.outgoing_edges) == 0

    def is_singleton(self):
        return self.is_root() and self.is_leaf() and not self.is_top

    def encode(self):
        json = {"id": self.id};
        if self.label:
            json["label"] = self.label;
        if self.properties:
            json["properties"] = self.properties;
        if self.anchors:
            json["anchors"] = self.anchors;
        return json;

    def dot(self, stream):
        if self.label or self.properties or self.anchors:
            print("  {} [ label=<<table align=\"center\" border=\"0\">".format(self.id),
                  end = "", file = stream);
            if self.label:
                print("<tr><td colspan=\"2\">{}</td></tr>".format(self.label),
                      end = "", file = stream);
            if self.anchors:
                print("<tr><td colspan=\"2\">", end = "", file = stream);
                for anchor in self.anchors:
                    if "from" in anchor and "to" in anchor:
                        print("{}〈{}:{}〉"
                              "".format("&thinsp;" if anchor != self.anchors[0] else "",
                                        anchor["from"], anchor["to"]),
                              end = "", file = stream);
                print("</td></tr>", end = "", file = stream);
            if self.properties:
                for name in self.properties:
                    print("<tr><td>{}</td><td>{}</td></tr>"
                          "".format(name, self.properties[name]), end = "", file = stream);
            print("</table>> ];", file = stream);
        else:
            print("  {} [ shape=point, width=0.2 ];".format(self.id), file = stream);

    def __key(self):
        return self.id

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __lt__(self, other):
        return self.__key() < other.__key()

    def __hash__(self):
        return hash(self.__key())

class Edge(object):

    def __init__(self, src, tgt, lab):
        self.src = src
        self.tgt = tgt
        self.lab = lab

    def is_loop(self):
        return self.src == self.tgt

    def min(self):
        return min(self.src, self.tgt)

    def max(self):
        return max(self.src, self.tgt)

    def endpoints(self):
        return self.min(), self.max()

    def length(self):
        return self.max() - self.min()

    def encode(self):
        json = {"source": self.src, "target": self.tgt, "label": self.lab};
        return json;

    def __key(self):
        return self.tgt, self.src, self.lab

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __lt__(self, other):
        return self.__key() < other.__key()

    def __hash__(self):
        return hash(self.__key())

class Graph(object):

    def __init__(self, id, flavor = None, framework = None):
        self.id = id
        self.input = None;
        self.nodes = []
        self.edges = set()
        self.flavor = flavor;
        self.framework = framework;

    def add_node(self, id = None, label = None, properties = None,
                 anchors = None, top = False):
        node = Node(id if id else len(self.nodes),
                    label = label, properties = properties,
                    anchors = anchors, top = top);
        self.nodes.append(node)
        return node

    def add_edge(self, src, tgt, lab):
        edge = Edge(src, tgt, lab)
        self.edges.add(edge)
        self.nodes[src].outgoing_edges.add(edge)
        self.nodes[tgt].incoming_edges.add(edge)
        return edge

    def encode(self):
        json = {"id": self.id};
        if self.flavor:
            json["flavor"] = self.flavor;
        if self.framework:
            json["framework"] = self.framework;
        if self.input:
            json["input"] = self.input;
        tops = [node.id for node in self.nodes if node.is_top];
        if len(tops):
            json["tops"] = tops;
        json["nodes"] = [node.encode() for node in self.nodes];
        json["edges"] = [edge.encode() for edge in self.edges];
        return json;

    def dot(self, stream):
        print("digraph \"{}\" {{\n  root [ style=invis ];"
              "".format(self.id),
              file = stream);
        for node in self.nodes:
            if node.is_top:
                print("  root -> {};".format(node.id), file = stream);
        for node in self.nodes:
            node.dot(stream);
        for edge in self.edges:
            print("  {} -> {} [ label=\"{}\" ];"
                  "".format(edge.src, edge.tgt,
                            edge.lab if edge.lab else ""),
                  file = stream);
        print("}", file = stream);
