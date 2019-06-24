import re
import sys

from graph import Graph
from smatch.amr import AMR;

def amr_lines(fp, alignment):
    id, snt, lines = None, None, [];
    alignment = read_alignment(alignment);
    for line in fp:
        line = line.strip();
        if len(line) == 0:
            if len(lines) > 0:
                i = mapping = None;
                try:
                    i, mapping = next(alignment);
                except:
                    print("amr_lines(): missing alignment for graph #{}."
                          "".format(id), file = sys.stderr);
                    pass;
                yield id, snt, " ".join(lines), \
                    mapping if mapping is not None and i == id else None;
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
        i = mapping = None;
        try:
            i, mapping = next(alignment);
        except:
            print("amr_lines(): missing alignment for graph #{}."
                  "".format(id), file = sys.stderr);
            pass;
        yield id, snt, " ".join(lines), \
            mapping if mapping is not None and i == id else None;

def read_alignment(stream):
    if stream is None:
        while True: yield None, None;
    else: 
        id = None;
        alignment = dict();
        for line in stream:
            line = line.strip();
            if len(line) == 0:
                yield id, alignment;
                id = None;
                alignment.clear();
            else:
                if line.startswith("#"):
                    if line.startswith("# ::id"):
                        id = line.split()[2];
                else:
                    fields = line.split("\t");
                    if len(fields) == 2:
                        start, end = fields[1].split("-");
                        span = set(range(int(start), int(end) + 1));
                        fields = fields[0].split();
                        if len(fields) > 1 and fields[1].startswith(":"):
                            fields[1] = fields[1][1:];
                            if fields[1] == "wiki": continue;
                        if fields[0] not in alignment: alignment[fields[0]] = bucket = dict();
                        else: bucket = alignment[fields[0]];
                        path = tuple(fields[1:]);
                        if path not in bucket: bucket[path] = can = set();
                        else: can =  bucket[path];
                        can |= span;
        yield id, alignment;

def amr2graph(id, amr, full = False, reify = False, alignment = None):
    graph = Graph(id, flavor = 2, framework = "amr")
    node2id = {}
    i = 0
    for n, v, a in zip(amr.nodes, amr.node_values, amr.attributes):
        j = i
        node2id[n] = j
        top = False;
        for key, val in a:
            if key == "TOP":
                top = True;
        node = graph.add_node(j, label = v, top=top)
        i += 1
        for key, val in a:
            if key != "TOP" \
               and (key not in {"wiki"} or full):
                if val.endswith("¦"):
                    val = val[:-1];
                if reify:
                    graph.add_node(i, label=val)
                    graph.add_edge(j, i, key)
                    i += 1
                else:
                    node.set_property(key, val);

    for src, r in zip(amr.nodes, amr.relations):
        for label, tgt in r:
            normal = None;
            if label == "mod":
                normal = "domain";
            elif label.endswith("-of-of") \
                 or label.endswith("-of") \
                   and label not in {"consist-of" "subset-of"} \
                   and not label.startswith("prep-"):
                normal = label[:-3];
            graph.add_edge(node2id[src], node2id[tgt], label, normal)

    overlay = None;
    if alignment is not None:
        overlay = Graph(id, flavor = 2, framework = "alignment");
        for node in alignment:
            for path, span in alignment[node].items():
                if len(path) == 0:
                    node = overlay.add_node(node2id[node], label = tuple(span));
        for node in alignment:
            i = node2id[node];
            for path, span in alignment[node].items():
                if len(path) == 1:
                    node = overlay.find_node(i);
                    if node is None: node = overlay.add_node(i);
                    node.set_property(path[0], tuple(span));
                elif len(path) > 1:
                    print("amr2graph(): ignoring alignment path {} on node #{} ({})"
                          "".format(path, source, node));

    return graph, overlay;

def convert_amr_id(id):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id)
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)))
    m = re.search(r'lpp_1943\.([0-9]+)', id)
    if m:
        return "1%04d0" % (int(m.group(1)))
    else:
        raise Exception('Could not convert id: %s' % id)

def read(fp, full = False, reify = False,
         text = None, alignment = None, quiet = False):
    n = 0;
    for id, snt, amr_line, mapping in amr_lines(fp, alignment):
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
        graph, overlay = amr2graph(id, amr, full, reify, mapping);
        cid = None;
        if text:
            graph.add_input(text, quiet = quiet);
        elif snt:
            graph.add_input(snt, quiet = quiet);
        yield graph, overlay;
