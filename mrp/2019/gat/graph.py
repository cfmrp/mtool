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
        self.nodes = []
        self.edges = set()
        self.flavor = flavor;
        self.framework = framework;

    def add_node(self, id = None, label = None, properties = None, anchors = None, top = False):
        node = Node(id if id else len(self.nodes),
                    label = label, properties = properties, anchors = anchors, top = top);
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
        tops = [node.id for node in self.nodes if node.is_top];
        if len(tops):
            json["tops"] = tops;
        json["nodes"] = [node.encode() for node in self.nodes];
        json["edges"] = [edge.encode() for edge in self.edges];
        return json;
