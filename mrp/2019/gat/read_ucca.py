from operator import attrgetter

from analyzer import Graph, analyze_cmd
from ucca.ioutil import get_passages_with_progress_bar
from ucca import layer0, layer1


def passage2graph(passage):
    graph = Graph(passage.ID)
    l0 = passage.layer(layer0.LAYER_ID)
    l1 = passage.layer(layer1.LAYER_ID)
    units = l0.all + l1.all
    unit_id_to_node_id = {unit.ID: node_id for node_id, unit in enumerate(units)}
    for _ in units:
        graph.add_node()
    for unit in units:
        for edge in unit:
            for tag in edge.tags:
                graph.add_edge(unit_id_to_node_id[unit.ID], unit_id_to_node_id[edge.child.ID], tag)
    for unit in l1.heads:
        graph.nodes[unit_id_to_node_id[unit.ID]].is_top = True
    graph.tokens = [terminal.text for terminal in sorted(l0.all, key=attrgetter("position"))]
    return graph


def read_ucca(fp):
    for passage in get_passages_with_progress_bar(map(str.strip, fp), desc="Analyzing"):
        yield passage2graph(passage)


analyze_cmd(read_ucca, ordered=True)
