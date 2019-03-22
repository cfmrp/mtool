import re
import sys

from graph import Graph
from . import smatch

def amr_lines(fp):
    id, lines = None, []
    for line in fp:
        line = line.strip()
        if len(line) == 0:
            if len(lines) > 0:
                yield id, " ".join(lines)
            id, lines = None, []
        else:
            if line.startswith("#"):
                if line.startswith("# ::id"):
                    id = line.split()[2]
            else:
                lines.append(line)

def amr2graph(id, amr):
    graph = Graph(id)
    node2id = {}
    i = 0
    for n, v, a in zip(amr.nodes, amr.node_values, amr.attributes):
        id = i
        node2id[n] = id
        graph.add_node(id, label = v, top=("TOP" in a))
        i += 1
        #
        # creating separate 'atom' nodes for the concepts and
        # 'instance' edges is how SMATCH scores (inspired by
        # EDM_n, i suspect), but really these extra elements of
        # structure seem superfluous, seeing as we have the
        # notion of a designated label property on nodes.
        #
#        graph.add_node(i, label=v)
#        graph.add_edge(id, i, "instance")
#        i += 1
        for key, val in a.items():
            if key != "TOP":
                graph.add_node(i, label=val)
                graph.add_edge(id, i, key)
                i += 1
    for src, r in zip(amr.nodes, amr.relations):
        for tgt, rel_name in r.items():
            graph.add_edge(node2id[src], node2id[tgt], rel_name)
    return graph

def convert_wsj_id(id):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id)
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)))
    else:
        raise Exception('Could not convert id: %s' % id)

def read(fp, text = None):
    for id, amr_line in amr_lines(fp):
        a = smatch.AMR.parse_AMR_line(amr_line)
        if not a:
            raise Exception("failed to parse #{} ({}); exit."
                            "".format(id, amr_line));
        graph = amr2graph(id, a);
        cid = None;
        try:
            cid = convert_wsj_id(id)
        except:
            pass
        if text and cid:
            graph.add_input(text, id = cid);
        yield graph;
