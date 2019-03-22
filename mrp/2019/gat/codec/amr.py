import smatch
import re
import sys

from graph import Graph

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

def amr2graph_old(id, amr):
    assert len(amr.nodes) == len(set(amr.nodes))
    graph = Graph(id)
    node2id = {}
    for i, node in enumerate(amr.nodes):
        node2id[node] = i
        graph.add_node()
    instance_triples, attribute_triples, relation_triples = smatch.get_triples()
    for type, arg1, arg2 in relation_triples:
        assert arg1 in node2id and arg2 in node2id
        src = node2id[arg1]
        tgt = node2id[arg2]
        edge = graph.add_edge(src, tgt, type)
    for type, arg1, _ in attribute_triples:
        if type == "TOP":
            graph.nodes[node2id[arg1]].is_top = True
    for type, arg1, arg2 in instance_triples:
        assert type == "instance"
        
    return graph

def amr2graph(id, amr):
    graph = Graph(id)
    node2id = {}
    i = 0
    for n, v, a in zip(amr.nodes, amr.node_values, amr.attributes):
        id = i
        node2id[n] = id
        graph.add_node(id, top=("TOP" in a))
        i += 1
        graph.add_node(i, label=v)
        graph.add_edge(id, i, "instance")
        i += 1
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

def read(fp):
    for id, amr_line in amr_lines(fp):
        try:
            converted_id = convert_wsj_id(id)
            #print("ID conversion: %s -> %s" % (id, converted_id), file=sys.stderr)
            id = converted_id
        except:
            pass
        try:
            a = smatch.AMR.parse_AMR_line(amr_line)
        except:
            #print("Ignoring %s" % id, file=sys.stderr)
            continue
        if a is not None:
            yield amr2graph(id, a)
