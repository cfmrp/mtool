import re;
import sys;

import codec.mrp;
from graph import Edge, Graph;
from smatch.amr import AMR;

STASH = re.compile(r'__[0-9]+__');
INDEX = re.compile(r'x([0-9]+)((:?_[0-9]+)*)');

def amr_lines(fp, camr, alignment):
    id, snt, lines = None, None, [];
    stash = dict();
    def _stash_(match):
        prefix, constant, suffix = match.groups();
        fields = constant.split("/");
        if fields[0] in stash:
            if stash[fields[0]][2] != fields[1]:
                raise Exception("amr_lines(): "
                                "ambiguously defined constant in graph #{}, "
                                "‘{}’: ‘{}’ vs. ‘{}’; exit."
                                "".format(id, fields[0],
                                          stash[fields[0]][2], fields[1]));
        else:
                stash[fields[0]] = (len(stash), fields[0], fields[1]);
        return "{}__{}__{}".format(prefix, stash[fields[0]][0], suffix);

    alignment = read_alignment(alignment);
    for line in fp:
        line = line.strip();
        if len(line) == 0:
            if len(lines) > 0:
                i = mapping = None;
                try:
                    i, mapping = next(alignment);
                except Exception as error:
                    print("amr_lines(): missing alignment for graph #{}."
                          "".format(id), file = sys.stderr);
                    pass;
                yield id, snt, " ".join(lines), stash.values(), \
                    mapping if mapping is not None and i == id else None;
            id, lines = None, []; stash.clear();
        else:
            if line.startswith("#"):
                if line.startswith("# ::id"):
                    id = line.split()[2];
                if line.startswith("# ::snt"):
                   snt = line[8:].strip();
            else:
                if camr:
                    line = re.sub(r'((?:^|[ \t]):[^( ]+)\([^ \t]*\)([ \t]|$)',
                                  "\\1\\2", line, count = 0);
                    line = re.sub(r'(^|[ \t])(x[0-9]+/[^ \t]+)([ \t]|$)',
                                  _stash_, line, count = 0);
                lines.append(line)
    if len(lines) > 0:
        i = mapping = None;
        try:
            i, mapping = next(alignment);
        except:
            print("amr_lines(): missing alignment for graph #{}."
                  "".format(id), file = sys.stderr);
            pass;
        yield id, snt, " ".join(lines), stash.values(), \
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
                        if fields[0] not in alignment:
                            alignment[fields[0]] = bucket = dict();
                        else: bucket = alignment[fields[0]];
                        path = tuple(fields[1:]);
                        if path not in bucket: bucket[path] = can = set();
                        else: can =  bucket[path];
                        can |= span;
        yield id, alignment;

def amr2graph(id, amr, text, stash, camr = False,
              full = False, reify = False, quiet = False, alignment = None):
    graph = Graph(id, flavor = 2, framework = "amr");
    node2id = dict();
    anchoring = list();

    i = 0;
    def _anchor_(form):
        nonlocal i;
        m = None;
        j = graph.input.find(form, i);
        if j >= i:
            i, m = j, len(form);
        else:
            base = form;
            k, l = len(graph.input), 0;
            for old, new in {("‘", "`"), ("‘", "'"), ("’", "'"), ("`", "'"),
                             ("“", "\""), ("”", "\""),
                             ("–", "--"), ("–", "---"), ("—", "---"),
                             ("…", "..."), ("…", ". . .")}:
                form = base.replace(old, new);
                j = graph.input.find(form, i);
                if j >= i and j < k: k, l = j, len(form);
            if k < len(graph.input): i, m = k, l;
        if m:
            match = {"from": i, "to": i + m}; 
            i += m;
            return match;
        else:
            raise Exception("failed to anchor |{}| in |{}|{}| ({})"
                            "".format(form, graph.input[:i],
                                      graph.input[i:], i));

    if text:
        graph.add_input(text, quiet = quiet);
        if camr:
            for token in graph.input.split(" "):
                anchoring.append(_anchor_(token));
    i = 0;
    for n, v, a in zip(amr.nodes, amr.node_values, amr.attributes):
        j = i;
        node2id[n] = j;
        top = False;
        for key, val in a:
            if key == "TOP":
                top = True;
        anchors = find_anchors(n, anchoring) if camr else None;
        node = graph.add_node(j, label = v, top = top, anchors = anchors);
        i += 1
        for key, val in a:
            if STASH.match(val) is not None:
                index = int(val[2:-2]);
                val = next(v for k, x, v in stash if k == index);
            if key != "TOP" and (key not in {"wiki"} or full):
                if val.endswith("¦"):
                    val = val[:-1];
                if reify:
                    graph.add_node(i, label = val);
                    graph.add_edge(j, i, key);
                    i += 1
                else:
                    #
                    # _fix_me_ 
                    # this assumes that properties are unique.  (1-apr-20; oe)
                    #
                    node.set_property(key.lower(), str(val).lower());

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
        overlay = Graph(id, flavor = -1, framework = "anchoring");
        for node in alignment:
            for path, span in alignment[node].items():
                if len(path) == 0:
                    anchors = [{"#": token} for token in span];
                    node = overlay.add_node(node2id[node], anchors = anchors);
        for node in alignment:
            id = node2id[node];
            for path, span in alignment[node].items():
                if len(path) == 1:
                    key = path[0].lower();
                    node = overlay.find_node(id);
                    if node is None: node = overlay.add_node(id);
                    reference = graph.find_node(id);
                    anchors = [{"#": token} for token in span];
                    if reference.properties is not None \
                       and key in reference.properties:
                        node.set_anchoring(key, anchors);
                    else:
                        edge = next(edge for edge in graph.edges if edge.lab.lower() == key and edge.src == id);
                        overlay.edges.add(Edge(edge.id, None, None, None, anchors = anchors));
                elif len(path) > 1:
                    print("amr2graph(): "
                          "ignoring alignment path {} on node #{} ({})"
                          "".format(path, source, node));

    return graph, overlay;

def find_anchors(index, anchors):
    result = list();
    for match in INDEX.finditer(index):
        i, suffix = match.group(1), match.group(2);
        i = int(i) - 1;
        if i >= len(anchors): continue;
        anchor = anchors[i];
        if suffix != "":
            fields = suffix[1:].split("_");
            start = anchor["from"];
            for field in fields:
                j = int(field);
                result.append({"from": start + j - 1, "to": start + j});
        else:
            result.append(anchor);
    return result if len(result) > 0 else None;

def convert_amr_id(id):
    m = re.search(r'wsj_([0-9]+)\.([0-9]+)', id);
    if m:
        return "2%04d%03d" % (int(m.group(1)), int(m.group(2)));
    m = re.search(r'lpp_1943\.([0-9]+)', id);
    if m:
        return "1%04d0" % (int(m.group(1)));
    else:
        raise Exception('Could not convert id: %s' % id);

def read(fp, full = False, reify = False, camr = False,
         text = None, alignment = None,
         quiet = False, trace = 0):
    n = 0;
    for id, snt, amr_line, stash, mapping in amr_lines(fp, camr, alignment):
        if trace:
            print("{}: {}".format(id, amr_line), file = sys.stderr);
        amr = AMR.parse_AMR_line(amr_line);
        if not amr:
            raise Exception("failed to parse #{} ‘{}’; exit."
                            "".format(id, amr_line));
        if id is not None:
            try:
                id = convert_amr_id(id);
            except:
                pass;
        else:
            id = n;
            n += 1;
        graph, overlay = amr2graph(id, amr, text or snt, stash,
                                   camr, full, reify, quiet, mapping);
        yield graph, overlay;
