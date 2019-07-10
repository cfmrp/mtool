import json
import os
import sys

from graph import Graph

def read(fp):
    for i, line in enumerate(fp):
        try:
            graph = Graph.decode(json.loads(line.rstrip()))
            yield graph, None
        except Exception as error:
            print("code.mrp.read(): ignoring line {}: {}"
                  "".format(i, error), file = sys.stderr);
