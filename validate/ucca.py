import sys

from validate.utilities import report


def test(graph, actions, stream=sys.stderr):
    n = 0
    for edge in graph.edges:
        if not isinstance(edge.label, str) or len(edge.label) == 0:
            n += 1
            report(graph,
                   "missing or invalid label",
                   edge=edge, stream=stream)
    return n
