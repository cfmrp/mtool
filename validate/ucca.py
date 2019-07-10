import sys

from validate.utilities import report


def test(graph, actions, stream=sys.stderr):
    n = 0
    for edge in graph.edges:
        if not isinstance(edge.lab, str) or len(edge.lab) == 0:
            n += 1
            report(graph,
                   "missing or invalid label",
                   edge=edge, framework = "UCCA", stream=stream)
    return n
