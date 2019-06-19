import re
import sys

from graph import Graph
from smatch.amr import AMR;

def amr_lines(fp):
    id, snt, lines = None, None, [];
    for line in fp:
        line = line.strip();
        if len(line) == 0:
            if len(lines) > 0:
                yield id, snt, " ".join(lines)
            id, lines = None, []
        else:
            if line.startswith("#"):
                if line.startswith("# ::id"):
                    id = line.split()[2]
                if line.startswith("# ::snt"):
                   snt = line[8:].strip();
            else:
                lines.append(line)
    if len(lines) > 0:
        yield id, snt, " ".join(lines)
def amr2graph(id, amr, full = False, reify = False):
    graph = Graph(id, flavor = 2, framework = "amr")
    node2id = {}
    i = 0
    for n, v, a in zip(amr.nodes, amr.node_values, amr.attributes):
        id = i
        node2id[n] = id
        top = False;
        for key, val in a:
            if key == "TOP":
                top = True;
        node = graph.add_node(id, label = v, top=top)
        i += 1
        for key, val in a:
            if key != "TOP" \
               and (key not in {"wiki"} or full):
                if val.endswith("¦"):
                    val = val[:-1];
                if reify:
                    graph.add_node(i, label=val)
                    graph.add_edge(id, i, key)
                    i += 1
                else:
                    node.set_property(key, val);

    for src, r in zip(amr.nodes, amr.relations):
        for label, tgt in r:
            normal = None;
            if label == "mod":
                normal = "domain";
            elif label.endswith("-of-of") \
                 or label.endswith("-of") and label not in {"consist-of" "subset-of"} \
                   and not label.startswith("prep-"):
                normal = label[:-3];
            graph.add_edge(node2id[src], node2id[tgt], label, normal)
    return graph

def convert_amr_id(id):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id)
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)))
    m = re.search(r'lpp_1943\.([0-9]+)', id)
    if m:
        return "1%04d0" % (int(m.group(1)))
    else:
        raise Exception('Could not convert id: %s' % id)

def read(fp, full = False, reify = False, text = None, quiet = False):
    n = 0;
    for id, snt, amr_line in amr_lines(fp):
        amr = AMR.parse_AMR_line(amr_line)
        if not amr:
            raise Exception("failed to parse #{} ({}); exit."
                            "".format(id, amr_line));
        try:
            if id is not None:
                id = convert_amr_id(id)
            else:
                id = n;
                n += 1;
        except:
            pass
        graph = amr2graph(id, amr, full, reify);
        cid = None;
        if text:
            graph.add_input(text, quiet = quiet);
        elif snt:
            graph.add_input(snt, quiet = quiet);
        yield graph;
