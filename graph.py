# -*- coding: utf-8; -*-

# GraphaLogue Analyzer
# Marco Kuhlmann <marco.kuhlmann@liu.se>
# Stephan Oepen <oe@ifi.uio.no>

from datetime import datetime;
import html;
import operator;
from pathlib import Path;
import sys;

import score.core;

#
# default values on edge attributes, which will be removed in normalization.
# because all constants are normalized to lowercase strings prior to testing
# for default values, we need to deal in the normalized values here.
#
ATTRIBUTE_DEFAULTS = {"remote": "false"};
FLAVORS = {"dm": 0, "psd": 0, "ptg": 0,
           "eds": 1, "ptg": 1, "ucca": 1,
           "amr": 2, "drg": 2};

class Node(object):

    def __init__(self, id, label = None, properties = None, values = None,
                 anchors = None, top = False, type = 1):
        self.id = id
        self.type = type;
        self.label = label;
        self.properties = properties;
        self.values = values;
        self.anchorings = None;
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

    def set_anchoring(self, name, value):
        if self.properties and self.anchorings:
            try:
                i = self.properties.index(name);
                self.anchorings[i] = value;
            except ValueError:
                self.properties.append(name);
                self.anchorings.append(value);
        else:
            self.properties = [name];
            self.anchorings = [value];

    def add_anchor(self, anchor):
        if anchor is not None:
            if self.anchors is None: self.anchors = [anchor];
            elif anchor not in self.anchors: self.anchors.append(anchor);

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
        #
        # keep track of node-local pieces of information that either occur in
        # both nodes (i.e. match), or only in the first or second of them.  in
        # guiding the MCES search, we (apparently) use the net gain of matching
        # pieces /minus/ those not matching on either side.  that does not lead
        # to monotonicity, in the sense of cumulative scores moving either up
        # or down as more node correspondences are fixed, but for guiding the
        # MCES search monotonicity fortunately is not a requirement either.
        #
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
        if self.properties and self.values or self.anchorings:
            json["properties"] = self.properties;
            if self.values:
                json["values"] = self.values;
            if self.anchorings:
                json["anchorings"] = self.anchorings;
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

    def dot(self, stream, input = None, ids = False, strings = False,
            errors = None, overlay = False):

        shapes = ["square", "oval", "diamond", "triangle"];

        if errors is not None and "correspondences" in errors:
            correspondences = {g: s for g, s in errors["correspondences"]};
        else:
            correspondences = None;
        missing = [None, [], [], None];
        surplus = [None, [], [], None];
        if errors is not None:
            if "labels" in errors and "missing" in errors["labels"]:
                for id, label in errors["labels"]["missing"]:
                    if id == self.id: missing[0] = label;
            if "properties" in errors and "missing" in errors["properties"]:
                for id, property, value in errors["properties"]["missing"]:
                    if id == self.id:
                        missing[1].append(property); missing[2].append(value);
            if "anchors" in errors and "missing" in errors["anchors"]:
                for id, anchor in errors["anchors"]["missing"]:
                    if id == self.id: missing[3] = anchor;
            if correspondences is not None and self.id in correspondences:
                key = correspondences[self.id];
                if "labels" in errors and "surplus" in errors["labels"]:
                    for id, label in errors["labels"]["surplus"]:
                        if id == key: surplus[0] = label;
                if "properties" in errors and "surplus" in errors["properties"]:
                    for id, property, value in errors["properties"]["surplus"]:
                        if id == key:
                            surplus[1].append(property); surplus[2].append(value);
                if "anchors" in errors and "surplus" in errors["anchors"]:
                    for id, anchor in errors["anchors"]["surplus"]:
                        if id == key: surplus[3] = anchor;

        if self.label \
           or ids and not overlay \
           or self.properties and self.values \
           or self.anchors \
           or missing[0] is not None or len(missing[1]) > 0 \
           or missing[3] is not None \
           or surplus[0] is not None or len(surplus[1]) > 0 \
           or surplus[3] is not None:

            if self.type in {0, 1, 2, 3}:
                shape = "shape={}, ".format(shapes[self.type]);
            else:
                shape = "";
            color = "color=blue, " if overlay else "";
            print("  {} [ {}{}label=<<table align=\"center\" border=\"0\" cellspacing=\"0\">"
                  "".format(self.id, shape, color), end = "", file = stream);

            if ids and not overlay:
                print("<tr><td colspan=\"2\">#{}</td></tr>"
                      "".format(self.id), end = "", file = stream);

            if self.label:
                if missing[0]: font = "<font color=\"red\">";
                elif overlay: font = "<font color=\"blue\">";
                else: font = "<font>";
                print("<tr><td colspan=\"2\">{}{}</font></td></tr>"
                      "".format(font, html.escape(self.label, False)),
                      end = "", file = stream);
            if surplus[0]:
                font = "<font color=\"blue\">";
                print("<tr><td colspan=\"2\">{}{}</font></td></tr>"
                      "".format(font, html.escape(surplus[0], False)),
                      end = "", file = stream);

            def __anchors__(anchors, color):
                print("<tr><td colspan=\"2\"><font color=\"{}\">{{"
                      "".format(color), end = "", file = stream);
                for index in anchors:
                    print("{}{}".format("&thinsp;" if index != anchors[0] else "", index),
                          end = "", file = stream);
                print("}</font></td></tr>", end = "", file = stream);
            if self.anchors is not None:
                if overlay:
                    __anchors__(self.anchors, "blue");
                else:
                    print("<tr><td colspan=\"2\">", end = "", file = stream);
                    for anchor in self.anchors:
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
                    print("</td></tr>", end = "", file = stream);

            if missing[3]: __anchors__(missing[3], "red");
            if surplus[3]: __anchors__(surplus[3], "blue");

            def __properties__(names, values, color):
                font = "<font color=\"{}\">".format(color);
                for name, value in zip(names, values):
                    print("<tr><td sides=\"l\" border=\"1\" align=\"left\">{}{}</font>"
                          "</td><td sides=\"r\" border=\"1\" align=\"left\">{}{}</font></td></tr>"
                          "".format(font, html.escape(name, False),
                                    font, html.escape(value), False),
                          end = "", file = stream);
            if self.properties and self.values:
                if not overlay:
                    for name, value in zip(self.properties, self.values):
                        i = None;
                        try:
                            i = missing[1].index(name);
                        except:
                            pass;
                        if i is None or missing[2][i] != value:
                            __properties__([name], [value], "black");
                else:
                    __properties__(self.properties, self.values, "blue");
            if len(missing[1]) > 0: __properties__(missing[1], missing[2], "red");
            if len(surplus[1]) > 0: __properties__(surplus[1], surplus[2], "blue");

            print("</table>> ];", file = stream);
        elif overlay is None or self.id < 0:
            shape = "{}, label=\" \"".format(shapes[0]) if self.type == 0 else "point";
            print("  {} [ shape={}, width=0.2 ];"
                  "".format(self.id, shape), file = stream);

    def __key(self):
        return self.id

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __lt__(self, other):
        return self.__key() < other.__key()

    def __hash__(self):
        return hash(self.__key())

class Edge(object):

    def __init__(self, id, src, tgt, lab, normal = None,
                 attributes = None, values = None, anchors = None):
        self.id = id;
        self.src = src;
        self.tgt = tgt;
        self.lab = lab;
        self.normal = normal;
        self.attributes = attributes;
        self.values = values;
        self.anchors = anchors;

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
            if self.normal is None \
                and self.lab is not None:
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
        json = {"id": self.id}
        if self.src is not None: json["source"] = self.src;
        if self.tgt is not None: json["target"] = self.tgt;
        if self.lab: json["label"] = self.lab;
        if self.normal: json["normal"] = self.normal;
        if self.attributes and self.values:
            json["attributes"] = self.attributes;
            json["values"] = self.values;
        if self.anchors: json["anchors"] = self.anchors;
        return json;

    @staticmethod
    def decode(json):
        id = json.get("id", None);
        src = json.get("source", None);
        tgt = json.get("target", None);
        lab = json.get("label", None);
        if lab == "": lab = None;
        normal = json.get("normal", None)
        attributes = json.get("attributes", None)
        properties = json.get("properties", None)
        if properties is not None:
            print("Edge 'properties' are deprecated. Use 'attributes' instead.", file=sys.stderr);
            if attributes is None:
                attributes = properties
        values = json.get("values", None)
        return Edge(id, src, tgt, lab, normal, attributes, values)

    def dot(self, stream, input = None, strings = False,
            errors = None, overlay = False):
        def __missing__():
            if errors is not None and "edges" in errors \
               and "missing" in errors["edges"]:
                for source, target, label in errors["edges"]["missing"]:
                    if source == self.src and target == self.tgt and label == self.lab:
                        return True;
            return False;
        if self.attributes and self.values:
            style = ", style=dashed";
            label = "<<table align=\"center\" border=\"0\" cellspacing=\"0\">";
            if self.lab: label += "<tr><td colspan=\"1\">{}</td></tr>".format(self.lab);
            #
            # _fix_me_
            # currently assuming that all values are boolean where presence of
            # the attribute means True.                         (oe; 21-apr-20)
            #
            if self.attributes and self.values:
                for attribute, _ in zip(self.attributes, self.values):
                    label += "<tr><td>{}</td></tr>".format(attribute);
            label += "</table>>";
        else:
            label = self.lab;
            if label and self.normal:
                if label[:-3] == self.normal:
                    label = "(" + self.normal + ")-of";
                else:
                    label = label + " (" + self.normal + ")";
            if label: label = "\"{}\"".format(label);
            style = "";
        if overlay:
            color = ", color=blue, fontcolor=blue";
        elif __missing__():
            color = ", color=red, fontcolor=red";
        else:
            color = "";
        print("  {} -> {} [ label={}{}{} ];"
              "".format(self.src, self.tgt, label if label else "\"\"",
                        style, color),
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
        self._provenance = None
        self._targets = None;
        self.input = None;
        self.nodes = [];
        self.edges = set();
        self.flavor = FLAVORS.get(framework) if flavor is None else flavor;
        self.framework = framework;

    def size(self):
        return len(self.nodes);

    def source(self, value = None):
        if value is not None: self._source = value;
        return self._source;

    def provenance(self, value = None):
        if value is not None: self._provenance = value;
        return self._provenance;

    def targets(self, value = None):
        if value is not None: self._targets = value;
        return self._targets;

    def inject(self, information):
        if isinstance(information, str): information = eval(information);
        for key, value in information.items():
            if key == "id": self.id = value;
            elif key == "time": self.item = value;
            elif key == "flavor": self.flavor = value;
            elif key == "framework": self.framework = value;
            elif key == "source": self._source = value;
            elif key == "provenance": self._provenance = value;
            elif key == "targets": self._targets = value;
            elif key == "input": self.input = value;
            else:
                print("Graph.inject(): ignoring invalid key ‘{}’"
                      "".format(key), file = sys.stderr);

    def add_node(self, id = None, label = None,
                 properties = None, values = None,
                 anchors = None, top = False, type = 1):
        node = Node(id if id is not None else len(self.nodes),
                    label = label, properties = properties, values = values,
                    anchors = anchors, top = top, type = type);
        self.nodes.append(node)
        return node

    def find_node(self, id):
        for node in self.nodes:
            if node.id == id: return node;

    def add_edge(self, src, tgt, lab, normal = None,
                 attributes = None, values = None):
        self.store_edge(Edge(len(self.edges), src, tgt, lab, normal, attributes, values));

    def store_edge(self, edge, robust = False):
        self.edges.add(edge)
        source = self.find_node(edge.src);
        if source is None and not robust:
            raise ValueError("Graph.add_edge(): graph #{}: "
                             "invalid source node {}."
                             "".format(self.id, self.src))
        if source: source.outgoing_edges.add(edge)
        target = self.find_node(edge.tgt);
        if target is None and not robust:
            raise ValueError("Graph.add_edge(): graph #{}: "
                             "invalid target node {}."
                             "".format(self.id, self.tgt))
        if target: target.incoming_edges.add(edge)
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
                    #
                    # _fix_me_
                    # the block below looks weird: it would seem to accept any
                    # of the punctuation marks given to scan(), irrespective
                    # of the current .form. value?             (oe; 27-apr-20)
                    #
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

    def prettify(self, trace = 0):
        if self.framework == "drg":
            boxes = {"IMP", "DIS", "DUP", "NOT", "POS", "NEC",
                     "ALTERNATION", "ATTRIBUTION", "BACKGROUND",
                     "COMMENTARY", "CONDITION", "CONTINUATION", "CONTRAST",
                     "CONSEQUENCE", "ELABORATION", "EXPLANATION", "INSTANCE",
                     "NARRATION", "NEGATION", "NECESSITY",
                     "POSSIBILITY", "PARALLEL", "PRECONDITION",
                     "RESULT", "TOPIC", "PRESUPPOSITION"};
            for node in self.nodes:
                if node.is_top or node.is_root():
                    node.type = 0;
                    for edge in node.outgoing_edges:
                        if edge.lab in boxes:
                            self.find_node(edge.tgt).type = 0;
                elif len(node.incoming_edges) == len(node.outgoing_edges) == 1:
                    if next(iter(node.incoming_edges)).lab is None \
                       and next(iter(node.outgoing_edges)).lab is None:
                        node.type = 2;

    def score(self, graph, correspondences, errors = None):

        #
        # accommodate the various conventions for node correspondence matrices;
        # anyway, entries are indices into the .nodes. list, not identifiers.
        # _fix_me_
        # double-check for correspondences from SMATCH.         (oe; 19-apr-20)
        #
        if isinstance(correspondences, list) and len(correspondences) > 0:
            if isinstance(correspondences[0], tuple):
                correspondences = {i: j if j is not None else -1
                                   for i, j in correspondences};
            elif isinstance(correspondences[0], int):
                correspondences = {i: j if j is not None else -1
                                   for i, j in enumerate(correspondences)};

        #
        # all tuples use node identifiers from the gold graph, where there is
        # a correspondence; otherwise we (appear to) synthesize new unique
        # identifiers for remaining nodes from both graphs.
        #
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

        #
        # map 'corresponding' identifiers back to the original graphs
        #
        def native(id, identities):
            for key, value in identities.items():
                if id == value: return key;

        def tuples(graph, identities):
            #
            # .identities. is a hash table mapping node identifiers into the
            # 'corresponding' identifier space, such that paired nodes (and
            # only these) share the same identifier.
            #
            def identify(id):
                return identities[id] if identities is not None else id;
            tops = set();
            labels = set();
            properties = set();
            anchors = set();
            edges = set();
            attributes = set();
            for node in graph.nodes:
                identity = identify(node.id);
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
                identity \
                    = (identify(edge.src), identify(edge.tgt), edge.lab);
                edges.add(identity);
                if edge.attributes and edge.values:
                    for attribute, value in zip(edge.attributes, edge.values):
                        attributes.add(tuple(list(identity) + [attribute, value]));
            return tops, labels, properties, anchors, edges, attributes;

        def count(gold, system, key):

            if errors is not None:
                missing = gold - system;
                surplus = system - gold;
                if len(missing) > 0 or len(surplus) > 0 and key not in errors:
                    errors[key] = dict();
                if key == "tops":
                    if missing:
                        errors[key]["missing"] \
                            = [native(id, identities1) for id in missing];
                    if surplus:
                        errors[key]["surplus"] \
                            = [native(id, identities2) for id in surplus];
                elif key == "labels":
                    if missing:
                        errors[key]["missing"] \
                            = [(native(id, identities1), label)
                               for id, label in missing];
                    if surplus:
                        errors[key]["surplus"] \
                            = [(native(id, identities2), label)
                               for id, label in surplus];
                elif key == "properties":
                    if missing:
                        errors[key]["missing"] \
                            = [(native(id, identities1), property, value)
                               for id, property,value in missing];
                    if surplus:
                        errors[key]["surplus"] \
                            = [(native(id, identities2), property, value)
                               for id, property, value in surplus];
                elif key == "anchors":
                    if missing:
                        errors[key]["missing"] \
                            = [(native(id, identities1), list(sorted(anchor)))
                               for id, anchor in missing];
                    if surplus:
                        errors[key]["surplus"] \
                            = [(native(id, identities2), list(sorted(anchor)))
                               for id, anchor in surplus];
                elif key == "edges":
                    if missing:
                        errors[key]["missing"] \
                            = [(native(source, identities1),
                                native(target, identities1), label)
                               for source, target, label in missing];
                    if surplus:
                        errors[key]["surplus"] \
                               = [(native(source, identities2),
                                   native(target, identities2), label)
                                  for source, target, label in surplus];
                elif key == "attributes":
                    if missing:
                        errors[key]["missing"] \
                            = [(native(source, identities1),
                                native(target, identities1), label,
                                attribute, value)
                               for source, target, label, attribute, value
                               in missing];
                    if surplus:
                        errors[key]["surplus"] \
                            = [(native(source, identities2),
                                native(target, identities2), label,
                                attribute, value)
                               for source, target, label, attribute, value
                               in surplus];
            return {"g": len(gold), "s": len(system), "c": len(gold & system)};

        if correspondences is None or len(correspondences) == 0:
            return count(set(), set()), count(set(), set()), \
                   count(set(), set()), count(set(), set()), \
                   count(set(), set()), count(set(), set());

        gtops, glabels, gproperties, ganchors, gedges, gattributes \
            = tuples(self, identities1);
        stops, slabels, sproperties, sanchors, sedges, sattributes \
            = tuples(graph, identities2);
        if errors is not None:
            errors[self.framework][self.id] = errors \
                = {"correspondences": [(self.nodes[g].id, graph.nodes[s].id)
                                       for g, s in correspondences.items() if s >= 0]}
        return count(gtops, stops, "tops"), count(glabels, slabels, "labels"), \
            count(gproperties, sproperties, "properties"), \
            count(ganchors, sanchors, "anchors"), \
            count(gedges, sedges, "edges"), \
            count(gattributes, sattributes, "attributes");

    def encode(self, version = 1.1):
        json = {"id": self.id};
        if self.flavor is not None:
            json["flavor"] = self.flavor;
        if self.framework:
            json["framework"] = self.framework;
        json["version"] = version;
        if self.time is not None:
            json["time"] = self.time.strftime("%Y-%m-%d");
        else:
            json["time"] = datetime.now().strftime("%Y-%m-%d");
        if self._source is not None: json["source"] = self._source;
        if self._provenance is not None: json["provenance"] = self._provenance;
        if self._targets is not None: json["targets"] = self._targets;
        if self.input:
            json["input"] = self.input;
        if self.nodes:
            tops = [node.id for node in self.nodes if node.is_top];
            if len(tops):
                json["tops"] = tops;
            json["nodes"] = [node.encode() for node in self.nodes];
            if self.edges:
                json["edges"] = [edge.encode() for edge in
                                 sorted(self.edges, key = operator.attrgetter("id"))];
        return json;

    @staticmethod
    def decode(json, robust = False):
        graph = Graph(json["id"], json.get("flavor"), json.get("framework"))
        try:
            graph.time = datetime.strptime(json["time"], "%Y-%m-%d")
        except:
            graph.time = datetime.strptime(json["time"], "%Y-%m-%d (%H:%M)")
        graph.input = json.get("input")
        graph.source(json.get("source"))
        graph.provenance(json.get("provenance"))
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
                if edge.id is None: edge.id = len(graph.edges);
                graph.store_edge(edge, robust = robust)
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

    def dot(self, stream, ids = False, strings = False,
            errors = None, overlay = False):
        if not overlay:
            print("digraph \"{}\" {{\n  top [ style=invis ];"
                  "".format(self.id),
                  file = stream);
        for node in self.nodes:
            if node.is_top:
                if overlay:
                    color = " [ color=blue ]";
                elif errors is not None and "tops" in errors \
                     and "missing" in errors["tops"] and node.id in errors["tops"]["missing"]:
                    color = " [ color=red ]";
                else:
                    color = "";
                print("  top -> {}{};".format(node.id, color), file = stream);
        n = -1;
        for node in self.nodes:
            node.dot(stream, self.input, ids, strings, errors, overlay);
            for edge in self.edges:
                if node.id == edge.src:
                    edge.dot(stream, self.input, strings, errors, overlay);

        if errors is not None:
            surplus = Graph(self.id, flavor = self.flavor, framework = self.framework);
            surplus.add_input(self.input);
            mapping = dict();
            correspondences = {s: g for g, s in errors["correspondences"]};
            if "labels" in errors and "surplus" in errors["labels"]:
                for id, label in errors["labels"]["surplus"]:
                    if id not in correspondences:
                        mapping[id] = surplus.add_node(id = n, label = label);
                        n -= 1;
            if "properties" in errors and "surplus" in errors["properties"]:
                for id, property, value in errors["properties"]["surplus"]:
                    if id not in correspondences:
                        if id in mapping:
                            mapping[id].set_property(property, value);
                        else:
                            mapping[id] = surplus.add_node(id = n,
                                                           properties = [property],
                                                           values = [value]);
                            n -= 1;
            if "anchors" in errors and "surplus" in errors["anchors"]:
                for id, anchor in errors["anchors"]["surplus"]:
                    if id not in correspondences:
                        if id in mapping:
                            mapping[id].anchors = anchor;
                        else:
                            mapping[id] = surplus.add_node(id = n, anchors = anchor);
                            n -= 1;
            if "tops" in errors and "surplus" in errors["tops"]:
                for id in errors["tops"]["surplus"]:
                    if id in correspondences:
                        print("  top -> {} [ color=blue ];"
                              "".format(correspondences[id]), file = stream);

                    elif id not in mapping:
                        mapping[id] = surplus.add_node(id = n, top = True);
                        n -= 1;
                    else:
                        mapping[id].is_root = True;
            if "edges" in errors and "surplus" in errors["edges"]:
                for source, target, label in errors["edges"]["surplus"]:
                    if source not in mapping:
                        try:
                            mapping[source] = surplus.add_node(correspondences[source]);
                        except KeyError:
                            mapping[source] = surplus.add_node(n);
                            n -= 1;
                    if target not in mapping:
                        try:
                            mapping[target] = surplus.add_node(correspondences[target]);
                        except KeyError:
                            mapping[target] = surplus.add_node(n);
                            n -= 1;
                    surplus.add_edge(mapping[source].id, mapping[target].id, label);
            surplus.dot(stream, ids = ids, strings = strings, errors = None, overlay = True);
        if not overlay: print("}", file = stream);
