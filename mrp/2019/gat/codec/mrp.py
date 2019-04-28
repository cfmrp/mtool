import json

from graph import Graph

def read(fp):
    for line in fp:
        yield Graph.decode(json.loads(line.rstrip()))
