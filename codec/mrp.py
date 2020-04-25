import json
import os
import sys

from graph import Graph

def read(fp, text = None):
    for i, line in enumerate(fp):
        try:
            graph = Graph.decode(json.loads(line.rstrip()))
            if text is not None: graph.add_input(text);
            yield graph, None
        except Exception as error:
            print("code.mrp.read(): ignoring line {}: {}"
                  "".format(i, error), file = sys.stderr);
