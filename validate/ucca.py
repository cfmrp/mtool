import sys

from validate.utilities import report


def is_primary(edge):
    for attribute, value in zip(edge.attributes, edge.values):
        if attribute == "remote" and value != "false":
            return True
    return False


def test(graph, actions, stream=sys.stderr):
    n = 0
    for edge in graph.edges:
        if not isinstance(edge.lab, str) or len(edge.lab) == 0:
            n += 1
            report(graph,
                   "missing or invalid label",
                   edge=edge, framework = "UCCA", stream=stream)
    roots = []
    for node in graph.nodes:
        primary = [edge for edge in node.incoming_edges if is_primary(edge)]
        primary_parents = [edge.src for edge in primary]
        if not primary:
            roots.append(node)
        elif len(primary_parents) > 1:
            n += 1
            report(graph,
                   "multiple primary parents for node",
                   node=node, edge=primary[0], framework="UCCA", stream=stream)
    if not roots:
        n += 1
        report(graph,
               "no roots in graph",
               framework="UCCA", stream=stream)
    elif len(roots) > 1:
        n += 1
        report(graph,
               "multiple roots in graph",
               node=roots[0], framework="UCCA", stream=stream)
    return n
