import re
import sys

from graph import Graph
from smatch.amr import AMR;

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

def amr2graph(id, amr, normalize = False):
    graph = Graph(id)
    node2id = {}
    i = 0
    for n, v, a in zip(amr.nodes, amr.node_values, amr.attributes):
        id = i
        node2id[n] = id
        #top = "TOP" in a;
        top = False;
        for key, val in a:
            if key == "TOP":
                top = True;
        graph.add_node(id, label = v, top=top)
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
#        for key, val in a.items():
        for key, val in a:
            if key != "TOP":
                if val.endswith("¦"):
                    val = val[:-1];
                graph.add_node(i, label=val)
                graph.add_edge(id, i, key)
                i += 1
    for src, r in zip(amr.nodes, amr.relations):
#        for tgt, rel_name in r.items():
        for label, tgt in r:
            normal = None;
            if label == "mod":
                normal = "domain";
            elif label.endswith("-of-of") \
                 or label.endswith("-of") and label != "consist-of" and not label.startswith("prep-"):
                normal = label[:-3];
            if normalize and normal:
                graph.add_edge(node2id[tgt], node2id[src], normal)
            else:
                graph.add_edge(node2id[src], node2id[tgt], label, normal)
    return graph

def convert_wsj_id(id):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id)
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)))
    else:
        raise Exception('Could not convert id: %s' % id)

def read(fp, normalize = False, text = None):
    for id, amr_line in amr_lines(fp):
        amr = AMR.parse_AMR_line(amr_line)
        if not amr:
            raise Exception("failed to parse #{} ({}); exit."
                            "".format(id, amr_line));
        graph = amr2graph(id, amr, normalize);
        cid = None;
        try:
            cid = convert_wsj_id(id)
        except:
            pass
        if text and cid:
            graph.add_input(text, id = cid);
        yield graph;
