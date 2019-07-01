import re;
from operator import attrgetter;
from pathlib import Path;

from graph import Graph;
from ucca import layer0, layer1;
from ucca.ioutil import get_passages;


def convert_id(id, prefix):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id);
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)));
    elif prefix:
        return prefix + id;
    else:
        return id;

def passage2graph(passage, text = None, prefix = None):
    graph = Graph(convert_id(passage.ID, prefix), flavor = 1, framework = "ucca");
    l0 = passage.layer(layer0.LAYER_ID);
    l1 = passage.layer(layer1.LAYER_ID);
    unit_id_to_node_id = {};

    n = None;
    if text:
        graph.add_input(text);
        n = len(graph.input);
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

    non_terminals = [unit for unit in l1.all if unit.tag in (layer1.NodeTags.Foundational, layer1.NodeTags.Punctuation)]
    for token in sorted(l0.all, key=attrgetter("position")):
        for unit in non_terminals:
            if not unit.attrib.get("implicit"):
                for edge in unit:
                    if "Terminal" in edge.tags and token.ID == edge.child.ID:
                        if unit.ID in unit_id_to_node_id:
                            node = graph.find_node(unit_id_to_node_id[unit.ID]);
                            if graph.input:
                                node.anchors.append(anchor(token.text));
                        else:
                            node = graph.add_node(anchors = [anchor(token.text)] if graph.input else None);
                            unit_id_to_node_id[unit.ID] = node.id;
    for unit in sorted(non_terminals, key=attrgetter("start_position", "end_position")):
        if not unit.attrib.get("implicit") and unit.ID not in unit_id_to_node_id:
            node = graph.add_node();
            unit_id_to_node_id[unit.ID] = node.id;
    for unit in non_terminals:
        for edge in unit:
            for tag in edge.tags:
                if tag != "Terminal":
                    if edge.child.ID in unit_id_to_node_id:
                        attributes, values = None, None;
                        if edge.attrib.get("remote"):
                            attributes = ["remote"];
                            values = [True];
                        graph.add_edge(unit_id_to_node_id[unit.ID],
                                       unit_id_to_node_id[edge.child.ID],
                                       tag,
                                       attributes = attributes,
                                       values = values);
                    else:
                        #
                        # quietly ignore edges to implicit nodes
                        #
                        pass;
    for unit in l1.heads:
        node_id = unit_id_to_node_id.get(unit.ID)
        if node_id is not None:
            graph.nodes[node_id].is_top = True;
    return graph

def read(fp, text = None, prefix = None):
    parent = Path(fp.name).parent;
    paths = [parent / file.strip() for file in fp];
    for passage in get_passages(map(str, paths)):
        try:
            graph = passage2graph(passage, text, prefix);
        except Exception as exception:
            print(exception);
            continue;
        yield graph, None;
