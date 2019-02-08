import re

from analyzer import Graph, analyze, analyze_cmd

EDS_MATCHER = re.compile(r'(.+?)(?<!\\):(.+)(?<!\\)\[(.*)(?<!\\)\]')

def read_instances(fp):
    sentence_id, top_handle, predicates = None, None, []
    # In the current version of the data, graphs are terminated by two
    # curly braces (each on a separate line) instead of just one.  The
    # purpose of the following flag is to implement sanity checks
    # (non-void sentence id, top handle, predicate list) under these
    # circumstances.  It can be removed once the data files are fixed.
    first_curly = True
    for line in fp:
        line = line.strip()
        if len(line) == 0:
            pass
        elif line.startswith("#"):
            sentence_id = line[1:]
            first_curly = True
        elif line.startswith("{"):
            colon = line.index(":")
            assert colon >= 0
            top_handle = line[1:colon].strip()
        elif line.endswith("}"):
            assert len(line) == 1
            if first_curly:
                assert sentence_id is not None
                assert top_handle is not None
                assert len(predicates) > 0
                yield (sentence_id, top_handle, predicates)
                sentence_id, top_handle, predicates = None, None, []
                first_curly = False
        else:
            match = EDS_MATCHER.match(line)
            assert match is not None
            node_id, label, arguments = match.groups()
            arguments = [tuple(arg.split()) for arg in arguments.split(',') if len(arg) > 0]
            predicates.append((node_id, label, arguments))

def instance2graph(instance):
    sentence_id, top, predicates = instance
    graph = Graph(sentence_id)
    handle2node = {}
    for handle, _, _ in predicates:
        assert handle not in handle2node
        handle2node[handle] = graph.add_node()
    handle2node[top].is_top = True
    for src_handle, _, arguments in predicates:
        src = handle2node[src_handle].id
        for relation, tgt_handle in arguments:
            tgt = handle2node[tgt_handle].id
            graph.add_edge(src, tgt, relation)
    graph.tokens = ['foo'] # TODO
    return graph

def read_edp(fp):
    for instance in read_instances(fp):
        yield instance2graph(instance)

analyze_cmd(read_edp, ordered=False)
