import json
import os

from graph import Graph

def read(fp):
    for line in fp:
        graph = Graph.decode(json.loads(line.rstrip()))
        yield graph, None
