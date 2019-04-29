# -*- coding: utf-8; -*-

# GraphaLogue Analyzer
# Marco Kuhlmann <marco.kuhlmann@liu.se>
# Stephan Oepen <oe@ifi.uio.no>

from datetime import datetime;
import html;
import itertools
from pathlib import Path;
import statistics
import sys;

from treewidth import quickbb

class Node(object):

    def __init__(self, id, label = None, properties = None, values = None,
                 anchors = None, top = False):
        self.id = id
        self.label = label;
        self.properties = properties;
        self.values = values;
        self.incoming_edges = set()
        self.outgoing_edges = set()
        self.anchors = anchors;
        self.is_top = top

    def set_property(self, name, value):
        if self.properties and self.values:
            try:
                i = self.properties.index(name);
                self.values[i] = value;
            except ValueError:
                self.properties.append(name);
                self.values.append(value);
        else:
            self.properties = [name];
            self.values = [value];

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
        if self.properties and self.values:
            json["properties"] = self.properties;
            json["values"] = self.values;
        if self.anchors:
            json["anchors"] = self.anchors;
        return json;

    @staticmethod
    def decode(json):
        id = json["id"]
        label = json.get("label", None)
        properties = json.get("properties", None)
        values = json.get("values", None)
        anchors = json.get("anchors", None)
        return Node(id, label, properties, values, anchors)

    def dot(self, stream, input = None, strings = False):
        if self.label \
           or self.properties and self.values \
           or self.anchors:
            print("  {} [ label=<<table align=\"center\" border=\"0\" cellspacing=\"0\">"
                  "".format(self.id),
                  end = "", file = stream);
            if self.label:
                print("<tr><td colspan=\"2\">{}</td></tr>"
                      "".format(html.escape(self.label, False)),
                      end = "", file = stream);
            if self.anchors:
                print("<tr><td colspan=\"2\">", end = "", file = stream);
                for anchor in self.anchors:
                    if "from" in anchor and "to" in anchor:
                        if strings and input:
                            print("{}<font face=\"Courier\">{}</font>"
                                  "".format(",&nbsp;" if anchor != self.anchors[0] else "",
                                            html.escape(input[anchor["from"]:anchor["to"]])),
                                  end = "", file = stream);
                        else:
                            print("{}〈{}:{}〉"
                                  "".format("&thinsp;" if anchor != self.anchors[0] else "",
                                            anchor["from"], anchor["to"]),
                                  end = "", file = stream);
                    elif False and isinstance(anchor, str):
                        print("{}<font face=\"Courier\">{}</font>"
                              "".format(",&nbsp;" if anchor != self.anchors[0] else "",
                                        html.escape(anchor)),
                              end = "", file = stream);
                print("</td></tr>", end = "", file = stream);
            if self.properties and self.values:
                for name, value in zip(self.properties, self.values):
                    print("<tr><td sides=\"l\" border=\"1\" align=\"left\">{}</td><td sides=\"r\" border=\"1\" align=\"left\">{}</td></tr>"
                          "".format(html.escape(name, False),
                                    html.escape(value), False),
                          end = "", file = stream);
            print("</table>> ];", file = stream);
        else:
            print("  {} [ shape=point, width=0.2 ];"
                  "".format(self.id), file = stream);

    def __key(self):
        return self.id

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __lt__(self, other):
        return self.__key() < other.__key()

    def __hash__(self):
        return hash(self.__key())

class Edge(object):

    def __init__(self, src, tgt, lab, normal = None,
                 properties = None, values = None):
        self.src = src;
        self.tgt = tgt;
        self.lab = lab;
        self.normal = normal;
        self.properties = properties;
        self.values = values;

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
        if self.normal:
            json["normal"] = self.normal;
        if self.properties and self.values:
            json["properties"] = self.properties;
            json["values"] = self.values;
        return json;

    @staticmethod
    def decode(json):
        src = json["source"]
        tgt = json["target"]
        lab = json["label"]
        normal = json.get("normal", None)
        properties = json.get("properties", None)
        values = json.get("values", None)
        return Edge(src, tgt, lab, normal, properties, values)
        
    def dot(self, stream, input = None, strings = False):
        label = self.lab;
        if label and self.normal:
            if label[:-3] == self.normal:
                label = "(" + self.normal + ")-of";
            else:
                label = label + " (" + self.normal + ")";
        style = "";
        if self.properties and "remote" in self.properties:
            style = ", style=dashed";
        print("  {} -> {} [ label=\"{}\"{} ];"
              "".format(self.src, self.tgt, label if label else "",
                        style),
              file = stream);
        
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
        self.id = id;
        self.time = datetime.utcnow();
        self.input = None;
        self.nodes = [];
        self.edges = set();
        self.flavor = flavor;
        self.framework = framework;

    def add_node(self, id = None, label = None,
                 properties = None, values = None,
                 anchors = None, top = False):
        node = Node(id if id else len(self.nodes),
                    label = label, properties = properties, values = values,
                    anchors = anchors, top = top);
        self.nodes.append(node)
        return node

    def find_node(self, id):
        for node in self.nodes:
            if node.id == id: return node;

    def add_edge(self, src, tgt, lab, normal = None,
                 properties = None, values = None):
        edge = Edge(src, tgt, lab, normal, properties, values)
        self.edges.add(edge)
        self.find_node(src).outgoing_edges.add(edge)
        self.find_node(tgt).incoming_edges.add(edge)
        return edge

    def add_input(self, text, id = None):
        if not id: id = self.id;
        if isinstance(text, str):
            self.input = text;
        elif isinstance(text, Path):
            file = text / (str(id) + ".txt");
            if not file.exists():
                print("add_input(): no text for {}.".format(file),
                      file = sys.stderr);
            else:
                with file.open() as stream:
                    input = stream.readline();
                    if input.endswith("\n"): input = input[:len(input) - 1];
                    self.input = input;
        else:
            input = text.get(id);
            if input:
                self.input = input;
            else:
                print("add_input(): no text for key {}.".format(id),
                      file = sys.stderr);

    def anchor(self):
        n = len(self.input);
        i = 0;

        def skip():
            nonlocal i;
            while i < n and self.input[i] in {" ", "\t"}:
                i += 1;

        def scan(candidates):
            for candidate in candidates:
                if self.input.startswith(candidate, i):
                    return len(candidate);

        skip();
        for node in self.nodes:
            for j in range(len(node.anchors) if node.anchors else 0):
                if isinstance(node.anchors[j], str):
                    form = node.anchors[j];
                    m = None;
                    if self.input.startswith(form, i):
                        m = len(form);
                    else:
                        for old, new in {("‘", "`"), ("’", "'")}:
                            form = form.replace(old, new);
                            if self.input.startswith(form, i):
                                m = len(form);
                                break;
                    if not m:
                        m = scan({"“", "\"", "``"}) or scan({"‘", "`"}) \
                            or scan({"”", "\"", "''"}) or scan({"’", "'"}) \
                            or scan({"—", "—", "---", "--"}) \
                            or scan({"…", "...", ". . ."});
                    if m:
                        node.anchors[j] = {"from": i, "to": i + m};
                        i += m;
                        skip();
                    else:
                        raise Exception("failed to anchor |{}| in |{}| ({})"
                                        "".format(form, self.input, i));

    def encode(self):
        json = {"id": self.id};
        if self.flavor != None:
            json["flavor"] = self.flavor;
        if self.framework:
            json["framework"] = self.framework;
        json["version"] = 0.9;
        json["time"] = self.time.strftime("%Y-%m-%d (%H:%M)");
        if self.input:
            json["input"] = self.input;
        tops = [node.id for node in self.nodes if node.is_top];
        if len(tops):
            json["tops"] = tops;
        json["nodes"] = [node.encode() for node in self.nodes];
        json["edges"] = [edge.encode() for edge in self.edges];
        return json;

    @staticmethod
    def decode(json):
        flavor = json.get("flavor", None)
        framework = json.get("framework", None)
        graph = Graph(json["id"], flavor, framework)
        graph.time = datetime.strptime(json["time"], "%Y-%m-%d (%H:%M)")
        graph.input = json.get("input", None)
        for j in json["nodes"]:
            node = Node.decode(j)
            graph.add_node(node.id, node.label, node.properties, node.values, node.anchors, top = False)
        for j in json["edges"]:
            edge = Edge.decode(j)
            graph.add_edge(edge.src, edge.tgt, edge.lab, edge.normal, edge.properties, edge.values)
        tops = json.get("tops", [])
        for i in tops:
            graph.find_node(i).is_top = True
        return graph

    def dot(self, stream, strings = False):
        print("digraph \"{}\" {{\n  top [ style=invis ];"
              "".format(self.id),
              file = stream);
        for node in self.nodes:
            if node.is_top:
                print("  top -> {};".format(node.id), file = stream);
        for node in self.nodes:
            node.dot(stream, self.input, strings);
        for edge in self.edges:
            edge.dot(stream, self.input, strings);
        print("}", file = stream);
