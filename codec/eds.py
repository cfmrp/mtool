import os.path;
import re;

from graph import Graph;

EDS_MATCHER = re.compile(r'(.+?)(?<!\\):(.+)(?<!\\)\[(.*)(?<!\\)\]')
PROPERTIES_MATCHER = re.compile(r"{(.+)}$");
CARG_MATCHER = re.compile(r'\(\"(.+)(?<!\\)"\)$');
LNK_MATCHER = re.compile(r"<([0-9]+):([0-9]+)>$");

def read_instances(fp):
    top_handle, predicates = None, [];
    sentence_id = None;
    try:
      sentence_id = int(os.path.splitext(os.path.basename(fp.name))[0]);
    except:
      pass;
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

def instance2graph(instance, reify = False, text = None):
    sentence_id, top, predicates = instance;
    anchors = None;
    graph = Graph(sentence_id, flavor = 1, framework = "eds");
    if text: graph.add_input(text);
    handle2node = {};
    for handle, label, _ in predicates:
        assert handle not in handle2node
        properties = None;
        values = None;
        match = PROPERTIES_MATCHER.search(label);
        if match:
            label = label[:match.start()];
            fields = match.group(1).replace(",", "").split();
            properties, values = list(), list();
            for i, field in enumerate(fields[1:]):
                if i % 2 == 0: properties.append(field);
                else: values.append(field);
        carg = None;
        match = CARG_MATCHER.search(label);
        if match:
            label = label[:match.start()];
            if not reify:
                properties = ["CARG"] + properties;
                values = [match.group(1)] + values;
            else:
                carg = match.group(1);
        anchors = None;
        match = LNK_MATCHER.search(label);
        if match:
            label = label[:match.start()];
            anchors = [{"from": int(match.group(1)), "to": int(match.group(2))}];
        handle2node[handle] = \
          graph.add_node(label = label, properties = properties, values = values, anchors = anchors);
        if carg and reify:
            carg = graph.add_node(label = carg, anchors = anchors);
            source = handle2node[handle].id;
            target = carg.id;
            graph.add_edge(source, target, "CARG");
    handle2node[top].is_top = True
    for src_handle, _, arguments in predicates:
        src = handle2node[src_handle].id
        for relation, tgt_handle in arguments:
            tgt = handle2node[tgt_handle].id
            graph.add_edge(src, tgt, relation)
    return graph

def read(fp, reify = False, text = None):
    for instance in read_instances(fp):
        yield instance2graph(instance, reify, text), None
