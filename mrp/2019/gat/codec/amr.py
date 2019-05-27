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

def amr2graph(id, amr, full = False, normalize = False, reify = False):
    graph = Graph(id, flavor = 2, framework = "amr")
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
        node = graph.add_node(id, label = v, top=top)
        i += 1
        #
        # creating separate 'atom' nodes for the concepts and 'instance' edges
        # is how SMATCH scores (inspired by # EDM_n, i suspect), but really
        # these extra elements of structure seem superfluous, seeing as we have
        # a notion of a designated label property on nodes.
        #
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
#        for tgt, rel_name in r.items():
        for label, tgt in r:
            normal = None;
            if label == "mod":
                normal = "domain";
            elif label.endswith("-of-of") \
                 or label.endswith("-of") and label not in {"consist-of" "subset-of"} \
                   and not label.startswith("prep-"):
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

def read(fp, full = False, normalize = False, reify = False, text = None):
    for id, snt, amr_line in amr_lines(fp):
        amr = AMR.parse_AMR_line(amr_line)
        if not amr:
            raise Exception("failed to parse #{} ({}); exit."
                            "".format(id, amr_line));
        try:
            id = convert_wsj_id(id)
        except:
            pass
        graph = amr2graph(id, amr, full, normalize, reify);
        cid = None;
        if text:
            graph.add_input(text);
        elif snt:
            graph.add_input(snt);
        yield graph;
