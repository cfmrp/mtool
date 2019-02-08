import re

from analyzer import Graph, analyze_cmd

# 1 = id (section, document, sentence), 2 = index of last token
S_PATTERN = r'<s id="(wsj_[0-9]{2}[0-9]{2}\.[0-9]+)"> ([0-9]+)'

# TODO: Normalize ID to SDP standard?

def read_ccd(fp):
    for line in fp:
        line = line.rstrip()
        if line.startswith("<s id="):
            match = re.match(S_PATTERN, line)
            assert match is not None
            graph = Graph(match.group(1))
            for _ in range(int(match.group(2))+1):
                node = graph.add_node()
                node.is_singleton = True
        elif line.startswith("<\s>"):
            yield graph
        else:
            columns = line.split()
            tgt = int(columns[0])
            src = int(columns[1])
            lab = "ARG-%d" % int(columns[3])
            edge = graph.add_edge(src, tgt, lab)
            graph.nodes[edge.src].is_singleton = False
            graph.nodes[edge.tgt].is_singleton = False

analyze_cmd(read_ccd, ordered=True)
