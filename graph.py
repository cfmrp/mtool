# -*- coding: utf-8; -*-

# GraphaLogue Analyzer
# Marco Kuhlmann <marco.kuhlmann@liu.se>
# Stephan Oepen <oe@ifi.uio.no>

import html;
import sys;
from datetime import datetime;
from pathlib import Path;

import score.core;

#
# default values on edge attributes, which will be removed in normalization.
# because all constants are normalized to lowercase strings prior to testing
# for default values, we need to deal in the normalized values here.
#
ATTRIBUTE_DEFAULTS = {"remote": "false"}
FLAVORS = {"dm": 0, "psd": 0, "eds": 1, "ucca": 1, "amr": 2}


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

    def normalize(self, actions, input = None, trace = 0):
        def trim(anchor, input):
            if "from" in anchor and "to" in anchor:
                i = max(anchor["from"], 0);
                j = min(anchor["to"], len(input));
                while i < j and input[i] in score.core.PUNCTUATION: i += 1;
                while j > i and input[j - 1] in score.core.PUNCTUATION: j -= 1;
                if trace and (i != anchor["from"] or j != anchor["to"]):
                    print("{} ({})--> <{}:{}> ({})"
                          "".format(anchor,
                                    input[anchor["from"]:anchor["to"]],
                                    i, j, input[i:j]));
                anchor["from"] = i;
                anchor["to"] = j;

        if self.anchors is not None and "anchors" in actions:
            if len(self.anchors) > 0 and input:
                for anchor in self.anchors: trim(anchor, input);
            elif len(self.anchors) == 0:
                self.anchors = None;    
        if "case" in actions:
            if self.label is not None:
                self.label = str(self.label).lower();
            if self.properties and self.values:
                for i in range(len(self.properties)):
                    self.properties[i] = str(self.properties[i]).lower();
                    self.values[i] = str(self.values[i]).lower();

    def compare(self, node):
        count1 = both = count2 = 0;
        if node is None:
            if self.is_top:
                count1 += 1;
            if self.label is not None:
                count1 += 1;
            if self.properties is not None:
                count1 += len(self.properties);
            return both - count1 - count2, count1, both, count2;
        if self.is_top:
            if node.is_top: both += 1;
            else: count1 += 1;
        else:
            if node.is_top: count2 += 1;
            else: both += 1;
        if self.label is not None:
            if self.label == node.label:
                both += 1;
            else:
                count1 += 1;
                if node.label is not None: count2 += 1;
        if self.properties is not None:
            if node.properties is None:
                count1 += len(self.properties);
            else:
                properties1 = {(property, self.values[i])
                               for i, property in enumerate(self.properties)};
                properties2 = {(property, node.values[i])
                               for i, property in enumerate(node.properties)};
                n = len(properties1 & properties2);
                count1 += len(properties1) - n;
                both += n;
                count2 += len(properties2) - n;
        elif node.properties is not None:
            count2 += len(node.properties);
        return both - count1 - count2, count1, both, count2;
                   
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

    def dot(self, stream, input = None, ids = False, strings = False):
        if self.label \
           or ids \
           or self.properties and self.values \
           or self.anchors:
            print("  {} [ label=<<table align=\"center\" border=\"0\" cellspacing=\"0\">"
                  "".format(self.id),
                  end = "", file = stream);
            if ids:
                print("<tr><td colspan=\"2\">#{}</td></tr>"
                      "".format(self.id), end = "", file = stream);
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
                 attributes = None, values = None):
        self.src = src;
        self.tgt = tgt;
        self.lab = lab;
        self.normal = normal;
        self.attributes = attributes;
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

    def normalize(self, actions, trace = 0):

        if "edges" in actions:
            if self.normal is None:
                label = self.lab;
                if label == "mod":
                    self.normal = "domain";
                elif label.endswith("-of-of") \
                     or label.endswith("-of") \
                     and label not in {"consist-of" "subset-of"} \
                     and not label.startswith("prep-"):
                    self.normal = label[:-3];
            if self.normal:
                target = self.src;
                self.src = self.tgt;
                self.tgt = target;
                self.lab = self.normal;
                self.normal = None;

        if "case" in actions:
            if self.lab is not None:
                self.lab = str(self.lab).lower();
            if self.normal is not None:
                self.normal = str(self.normal).lower();
            if self.attributes and self.values:
                for i in range(len(self.attributes)):
                    self.attributes[i] = str(self.attributes[i]).lower();
                    self.values[i] = str(self.values[i]).lower();

        if "attributes" in actions and self.attributes and self.values:
            # Drop (attribute, value) pairs whose value is the default value
            attribute_value_pairs = [
                (attribute, value) for attribute, value
                in zip(self.attributes, self.values)
                if attribute not in ATTRIBUTE_DEFAULTS
                   or ATTRIBUTE_DEFAULTS[attribute] != value]
            self.attributes, self.values = tuple(map(list, zip(*attribute_value_pairs))) or ([], [])

    def encode(self):
        json = {"source": self.src, "target": self.tgt, "label": self.lab};
        if self.normal:
            json["normal"] = self.normal;
        if self.attributes and self.values:
            json["attributes"] = self.attributes;
            json["values"] = self.values;
        return json;

    @staticmethod
    def decode(json):
        src = json["source"]
        tgt = json["target"]
        lab = json["label"]
        normal = json.get("normal", None)
        attributes = json.get("attributes", None)
        #
        # backwards compatibility with earlier MRP serialization (version 0.9)
        #
        if attributes is None: attributes = json.get("properties", None)
        values = json.get("values", None)
        return Edge(src, tgt, lab, normal, attributes, values)
        
    def dot(self, stream, input = None, strings = False):
        label = self.lab;
        if label and self.normal:
            if label[:-3] == self.normal:
                label = "(" + self.normal + ")-of";
            else:
                label = label + " (" + self.normal + ")";
        style = "";
        if self.attributes and "remote" in self.attributes:
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
        self._source = None;
        self._targets = None;
        self.input = None;
        self.nodes = [];
        self.edges = set();
        self.flavor = FLAVORS.get(framework) if flavor is None else flavor;
        self.framework = framework;

    def source(self, value = None):
        if value is not None: self._source = value;
        return self._source;
    
    def targets(self, value = None):
        if value is not None: self._targets = value;
        return self._targets;

    def add_node(self, id = None, label = None,
                 properties = None, values = None,
                 anchors = None, top = False):
        node = Node(id if id is not None else len(self.nodes),
                    label = label, properties = properties, values = values,
                    anchors = anchors, top = top);
        self.nodes.append(node)
        return node

    def find_node(self, id):
        for node in self.nodes:
            if node.id == id: return node;

    def add_edge(self, src, tgt, lab, normal = None,
                 attributes = None, values = None):
        edge = Edge(src, tgt, lab, normal, attributes, values)
        source = self.find_node(src);
        if source is None:
            raise ValueError("Graph.add_edge(): graph #{}: "
                             "invalid source node {}."
                             "".format(self.id, src))
        target = self.find_node(tgt);
        if target is None:
            raise ValueError("Graph.add_edge(): graph #{}: "
                             "invalid target node {}."
                             "".format(self.id, tgt))
        self.edges.add(edge)
        source.outgoing_edges.add(edge)
        target.incoming_edges.add(edge)
        return edge

    def add_input(self, text, id = None, quiet = False):
        if not id: id = self.id;
        if isinstance(text, str):
            self.input = text;
        elif isinstance(text, Path):
            file = text / (str(id) + ".txt");
            if not file.exists() and not quiet:
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
            elif not quiet:
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
                        for old, new in {("‘", "`"), ("’", "'"), ("`", "'"),
                                         ("“", "\""), ("”", "\"")}:
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

    def normalize(self, actions, trace = 0):
        for node in self.nodes:
            node.normalize(actions, self.input, trace);
        for edge in self.edges:
            edge.normalize(actions, trace);
        #
        # recompute cached edge relations, to reflect the new state of affairs
        #
        if "edges" in actions:
            for node in self.nodes:
                node.outgoing_edges.clear();
                node.incoming_edges.clear();
            for edge in self.edges:
                self.find_node(edge.src).outgoing_edges.add(edge);
                self.find_node(edge.tgt).incoming_edges.add(edge);

    def score(self, graph, correspondences):
        def tuples(graph, identities):
            tops = set();
            labels = set();
            properties = set();
            anchors = set();
            edges = set();
            attributes = set();
            for node in graph.nodes:
                identity = identities[node.id];
                if node.is_top: tops.add(identity);
                if node.label is not None: labels.add((identity, node.label));
                if node.properties is not None:
                    for property, value in zip(node.properties, node.values):
                        properties.add((identity, property, value.lower()));
                if node.anchors is not None:
                    anchor = score.core.anchor(node);
                    if graph.input:
                        anchor = score.core.explode(graph.input, anchor);
                    anchors.add((identity, anchor));
            for edge in graph.edges:
                edges.add((identities[edge.src], identities[edge.tgt],
                           edge.lab));
                if edge.attributes and edge.values:
                    identity \
                        = [identities[edge.src], identities[edge.tgt], edge.lab];
                    for attribute, value in zip(edge.attributes, edge.values):
                        attributes.add(tuple(identity + [attribute, value]));
            return tops, labels, properties, anchors, edges, attributes;

        def count(gold, system):
            return {"g": len(gold), "s": len(system), "c": len(gold & system)};

        if correspondences is None or len(correspondences) == 0:
            return count(set(), set()), count(set(), set()), \
                   count(set(), set()), count(set(), set()), \
                   count(set(), set()), count(set(), set());
            
        #
        # accommodate the various conventions for node correspondence matrices
        #
        if isinstance(correspondences, list) and len(correspondences) > 0:
            if isinstance(correspondences[0], tuple):
                correspondences = {i: j if j is not None else -1
                                   for i, j in correspondences};
            elif isinstance(correspondences[0], int):
                correspondences = {i: j if j is not None else -1
                                   for i, j in enumerate(correspondences)};
        identities1 = dict();
        identities2 = dict();
        for i, pair in enumerate(correspondences.items()):
            identities1[self.nodes[pair[0]].id] = i;
            if pair[1] >= 0:
                identities2[graph.nodes[pair[1]].id] = i;
        i = len(correspondences);
        for node in self.nodes:
            if node.id not in identities1:
                identities1[node.id] = i;
                i += 1;
        for node in graph.nodes:
            if node.id not in identities2:
                identities2[node.id] = i;
                i += 1;

        gtops, glabels, gproperties, ganchors, gedges, gattributes \
            = tuples(self, identities1);
        stops, slabels, sproperties, sanchors, sedges, sattributes \
            = tuples(graph, identities2);
        return count(gtops, stops), count(glabels, slabels), \
            count(gproperties, sproperties), count(ganchors, sanchors), \
            count(gedges, sedges), count(gattributes, sattributes);

    def encode(self):
        json = {"id": self.id};
        if self.flavor is not None:
            json["flavor"] = self.flavor;
        if self.framework:
            json["framework"] = self.framework;
        json["version"] = 1.0;
        json["time"] = self.time.strftime("%Y-%m-%d");
        if self._source is not None: json["source"] = self._source;
        if self._targets is not None: json["targets"] = self._targets;
        if self.input:
            json["input"] = self.input;
        if self.nodes:
            tops = [node.id for node in self.nodes if node.is_top];
            if len(tops):
                json["tops"] = tops;
            json["nodes"] = [node.encode() for node in self.nodes];
            if self.edges:
                json["edges"] = [edge.encode() for edge in self.edges];
        return json;

    @staticmethod
    def decode(json):
        graph = Graph(json["id"], json.get("flavor"), json.get("framework"))
        try:
            graph.time = datetime.strptime(json["time"], "%Y-%m-%d")
        except:
            graph.time = datetime.strptime(json["time"], "%Y-%m-%d (%H:%M)")
        graph.input = json.get("input")
        graph.source(json.get("source"))
        graph.targets(json.get("targets"))
        nodes = json.get("nodes")
        if nodes is not None:
            for j in nodes:
                node = Node.decode(j)
                graph.add_node(node.id, node.label, node.properties,
                               node.values, node.anchors, top = False)
        edges = json.get("edges")
        if edges is not None:
            for j in edges:
                edge = Edge.decode(j)
                graph.add_edge(edge.src, edge.tgt, edge.lab, edge.normal,
                               edge.attributes, edge.values)
        tops = json.get("tops")
        if tops is not None:
            for i in tops:
                node = graph.find_node(i)
                if node is not None:
                    node.is_top = True
                else:
                    raise ValueError("Graph.decode(): graph #{}: "
                                     "invalid top node {}."
                                     "".format(graph.id, i))
        return graph

    def dot(self, stream, ids = False, strings = False):
        print("digraph \"{}\" {{\n  top [ style=invis ];"
              "".format(self.id),
              file = stream);
        for node in self.nodes:
            if node.is_top:
                print("  top -> {};".format(node.id), file = stream);
        for node in self.nodes:
            node.dot(stream, self.input, ids, strings);
        for edge in self.edges:
            edge.dot(stream, self.input, strings);
        print("}", file = stream);
