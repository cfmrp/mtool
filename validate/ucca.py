import sys

from validate.utilities import report

CATEGORIES = {'H', 'A', 'P', 'S', 'D', 'G', 'C', 'E', 'F', 'N', 'R', 'T', 'Q', 'L', 'U'}


def is_primary(edge):
    for attribute, value in zip(edge.attributes or (), edge.values or ()):
        if attribute == "remote" and value != "false":
            return False
    return True


def is_implicit(node):
    for prop, value in zip(node.properties or (), node.values or ()):
        if prop == "implicit" and value != "false":
            return True
    return False


def test(graph, actions, stream=sys.stderr):
    n = 0
    for edge in graph.edges:
        if not isinstance(edge.lab, str) or len(edge.lab) == 0:
            n += 1
            report(graph,
                   "missing or invalid label",
                   edge=edge, framework="UCCA", stream=stream)
        elif edge.lab.upper() not in CATEGORIES:
            n += 1
            report(graph,
                   "edge label is not a UCCA category",
                   edge=edge, framework="UCCA", stream=stream)
        if edge.is_loop():
            n += 1
            report(graph,
                   "loop edge",
                   edge=edge, framework="UCCA", stream=stream)
    roots = []
    for node in graph.nodes:
        primary = [edge for edge in node.incoming_edges if is_primary(edge)]
        primary_parents = {edge.src for edge in primary}
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
    else:
        for node in roots:
            remotes = [edge for edge in node.incoming_edges if not is_primary(edge)]
            if remotes:
                n += 1
                report(graph,
                       "root has remote parents",
                       node=node, edge=remotes[0], framework="UCCA", stream=stream)
    for node in graph.nodes:
        if node.is_leaf() and not node.anchors and not is_implicit(node):
            n += 1
            report(graph,
                   "unanchored non-implicit node",
                   node=node, framework="UCCA", stream=stream)
    return n
