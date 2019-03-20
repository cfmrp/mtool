import re

import os.path;
from analyzer import Graph, analyze, analyze_cmd

EDS_MATCHER = re.compile(r'(.+?)(?<!\\):(.+)(?<!\\)\[(.*)(?<!\\)\]')

def read_instances(fp):
    top_handle, predicates = None, [];
    sentence_id = None;
    try:
      sentence_id = int(os.path.splitext(os.path.basename(fp.name))[0]);
    except:
      pass;
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
            predicates.append((node_id, label.strip(), arguments))

LNK_MATCHER = re.compile(r"<([0-9]+):([0-9]+)>$");

def instance2graph(instance):
    sentence_id, top, predicates = instance
    anchors = None;
    graph = Graph(sentence_id, flavor = 1, framework = "eds")
    handle2node = {}
    for handle, label, _ in predicates:
        assert handle not in handle2node
        lnk = LNK_MATCHER.search(label);
        if lnk:
          label = label[:lnk.start()];
          anchors = [{"from": lnk.group(1), "to": lnk.group(2)}];
        handle2node[handle] = \
          graph.add_node(label = label, anchors = anchors);
    handle2node[top].is_top = True
    for src_handle, _, arguments in predicates:
        src = handle2node[src_handle].id
        for relation, tgt_handle in arguments:
            tgt = handle2node[tgt_handle].id
            graph.add_edge(src, tgt, relation)
    graph.tokens = ['foo'] # TODO
    return graph

def read_eds(fp):
    for instance in read_instances(fp):
        yield instance2graph(instance)
