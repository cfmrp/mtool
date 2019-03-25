from operator import attrgetter
from pathlib import Path
import re

from graph import Graph;
from ucca import layer0, layer1
from ucca.ioutil import get_passages_with_progress_bar

def convert_wsj_id(id):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id)
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)))
    else:
        return id

def passage2graph(passage, text = None):
    graph = Graph(convert_wsj_id(passage.ID))
    l0 = passage.layer(layer0.LAYER_ID)
    l1 = passage.layer(layer1.LAYER_ID)
    units = l0.all + l1.all
    unit_id_to_node_id = {}
    for unit in l0.all:
        node = graph.add_node(label = unit.text, anchors = unit.text)
        unit_id_to_node_id[unit.ID] = node.id
    for unit in l1.all:
        if not unit.attrib.get("implicit"):
            node = graph.add_node()
            unit_id_to_node_id[unit.ID] = node.id
    for unit in l1.all:
        for edge in unit:
            for tag in edge.tags:
                if edge.child.ID in unit_id_to_node_id:
                    graph.add_edge(unit_id_to_node_id[unit.ID], unit_id_to_node_id[edge.child.ID], tag)
    for unit in l1.heads:
        graph.nodes[unit_id_to_node_id[unit.ID]].is_top = True
    if text:
        graph.add_input(text)
        graph.anchor()
    return graph

def read(fp, text = None):
    parent = Path(fp.name).parent;
    paths = {parent / file.strip() for file in fp};
    for passage in get_passages(map(str, paths), desc="Analyzing"):
        yield passage2graph(passage, text);


