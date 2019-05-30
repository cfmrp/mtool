# SemEval-2015 Task on Semantic Dependency Parsing
# Scorer
#
# Usage: python3 score.py GOLD_FILE SYSTEM_FILE [OPTIONS...]
#
# Marco Kuhlmann <marco.kuhlmann@liu.se>

import sys

UNLABELED = "-UNLABELED-"
VIRTUAL = "-VIRTUAL-"

class Node(object):

    def __init__(self):
        self.incoming_edges = set()
        self.outgoing_edges = set()

class Edge(object):

    def __init__(self, source, target, label):
        self.src = source
        self.tgt = target
        self.lab = label

    def __key(self):
        return (self.tgt, self.src, self.lab)

    def __eq__(self, other):
        return self.__key() == self.__key()

    def __hash__(self):
        return hash(self.__key())

    def __lt__(self, other):
        return self.__key() < other.__key()

class Graph(object):

    def __init__(self):
        pass

def make_graph(raw_graph):
    graph = Graph()
    graph.id = raw_graph[0]
    n_nodes = len(raw_graph) - 1
    graph.nodes = [None]
    graph.edges = set()
    predicates = []
    for i, token in enumerate(raw_graph[1:]):
        node = Node()
        node.id = int(token[0])
        node.form = token[1]
        node.lemma = token[2]
        node.pos = token[3]
        node.top = token[4] == '+'
        node.pred = token[5] == '+'
        node.sense = token[6]
        graph.nodes.append(node)
        if node.pred:
            predicates.append(i+1)
    for tgt, token in enumerate(raw_graph[1:], start=1):
        for pred, label in enumerate(token[7:]):
            if label != '_':
                src = predicates[pred]
                edge = Edge(src, tgt, label)
                graph.edges.add(edge)
                node.incoming_edges.add(edge)
                graph.nodes[src].outgoing_edges.add(edge)
    return graph

def read_graph(file):
    graph = []
    for line in file:
        line = line.rstrip()
        if len(line) == 0:
            assert len(graph) > 0 and graph[0].startswith("#")
            return graph
        else:
            if line.startswith("#"):
                assert len(graph) == 0
                graph.append(line)
            else:
                graph.append(line.split("\t"))
    return None

def read_graphs(file):
    line = file.readline().rstrip()
    assert line.startswith("#SDP")
    graph = read_graph(file)
    while graph:
        yield graph
        graph = read_graph(file)

def make_undirected(edge):
    src = min(edge[0], edge[1])
    tgt = max(edge[0], edge[1])
    return Edge(src, tgt, edge.lab)

def make_unlabeled(edge):
    return Edge(edge.src, edge.tgt, UNLABELED)

def add_virtual(graph):
    for node in graph.nodes[1:]:
        if node.top:
            graph.edges.add(Edge(0, node.id, VIRTUAL))
    return graph

class Measure(object):

    def __init__(self, get_items):
        self.get_items = get_items
        self.g = 0
        self.s = 0
        self.c = 0
        self.n_updates = 0
        self.n_matches = 0

    def update(self, gold, system):
        g_items = set(self.get_items(gold))
        s_items = set(self.get_items(system))
        self.g += len(g_items)
        self.s += len(s_items)
        self.c += len(g_items & s_items)
        self.n_updates += 1
        self.n_matches += g_items == s_items

    def p(self):
        return self.c / self.s if self.s != 0 else float('NaN')

    def r(self):
        return self.c / self.g if self.g != 0 else float('NaN')

    def f(self):
        p = self.p()
        r = self.r()
        return 2 * p * r / (p + r) if p + r != 0 else float('NaN')

    def m(self):
        return self.n_matches / self.n_updates if self.n_updates != 0 else float('NaN')

def LOG(msg=""):
    sys.stderr.write("%s\n" % msg)

def argument_predicate_dm(label):
    return True

def argument_predicate_pas(label):
    arguments = set("adj_ARG1 adj_ARG2 adj_MOD coord_ARG1 coord_ARG2 prep_ARG1 prep_ARG2 prep_ARG3 prep_MOD verb_ARG1 verb_ARG2 verb_ARG3 verb_ARG4 verb_MOD".split())
    return label in arguments

def argument_predicate_psd(label):
    return label.endswith("-arg")

class Scorer(object):

    def __init__(self):
        self.measureL = Measure(self.get_itemsL)
        self.measureU = Measure(self.get_itemsU)
        self.measureP = Measure(self.get_itemsP)
        self.measureF = Measure(self.get_itemsF)
        self.measureS = Measure(self.get_itemsS)

    def get_itemsL(self, graph):
        return graph.edges

    def get_itemsU(self, graph):
        return {(edge.src, edge.tgt) for edge in self.get_itemsL(graph)}

    def get_itemsP(self, graph):
        return {(frame[0], frame[2]) for frame in self.get_itemsF(graph)}

    def get_itemsF(self, graph):
        result = set()
        for node in graph.nodes[1:]:
            if self.has_scorable_predicate(node):
                arguments = set()
                for edge in node.outgoing_edges:
                    if self.argument_predicate(edge.lab):
                        arguments.add(edge)
                extract = (node.id, node.sense, tuple(sorted(arguments)))
                result.add(extract)
        return result

    def get_itemsS(self, graph):
        return {(frame[0], frame[1]) for frame in self.get_itemsF(graph)}

    def argument_predicate(self, label):
        return True

    def has_scorable_predicate(self, node):
        return node.pred and node.pos.startswith("V") ## and node.sense != "_"

    def show_predications(self, g):
        print(g.id)
        report_predications(self.complete_predications(g))

    def update(self, g, s):
        self.measureL.update(g, s)
        self.measureU.update(g, s)
        self.measureP.update(g, s)
        self.measureF.update(g, s)
        self.measureS.update(g, s)

    def report(self):
        LOG("### Labeled scores")
        LOG()
        LOG("Number of edges in gold standard: %d" % self.measureL.g)
        LOG("Number of edges in system output: %d" % self.measureL.s)
        LOG("Number of edges in common: %d" % self.measureL.c)
        LOG()
        LOG("LP: %.6f" % self.measureL.p())
        LOG("LR: %.6f" % self.measureL.r())
        LOG("LF: %.6f" % self.measureL.f())
        LOG("LM: %.6f" % self.measureL.m())
        LOG()

        LOG("### Unlabeled scores")
        LOG()
        LOG("Number of unlabeled edges in gold standard: %d" % self.measureU.g)
        LOG("Number of unlabeled edges in system output: %d" % self.measureU.s)
        LOG("Number of unlabeled edges in common: %d" % self.measureU.c)
        LOG()
        LOG("UP: %.6f" % self.measureU.p())
        LOG("UR: %.6f" % self.measureU.r())
        LOG("UF: %.6f" % self.measureU.f())
        LOG("UM: %.6f" % self.measureU.m())
        LOG()

        LOG("### Complete predications")
        LOG()
        LOG("Number of complete predications in gold standard: %d" % self.measureP.g)
        LOG("Number of complete predications in system output: %d" % self.measureP.s)
        LOG("Number of complete predications in common: %d" % self.measureP.c)
        LOG()
        LOG("PP: %.6f" % self.measureP.p())
        LOG("PR: %.6f" % self.measureP.r())
        LOG("PF: %.6f" % self.measureP.f())
        LOG()
    
        LOG("### Semantic frames")
        LOG()
        LOG("Number of semantic frames in gold standard: %d" % self.measureF.g)
        LOG("Number of semantic frames in system output: %d" % self.measureF.s)
        LOG("Number of semantic frames in common: %d" % self.measureF.c)
        LOG()
        LOG("FP: %.6f" % self.measureF.p())
        LOG("FR: %.6f" % self.measureF.r())
        LOG("FF: %.6f" % self.measureF.f())
        LOG()

        LOG("### Senses")
        LOG()
        LOG("Number of senses in gold standard: %d" % self.measureS.g)
        LOG("Number of senses in system output: %d" % self.measureS.s)
        LOG("Number of senses in common: %d" % self.measureS.c)
        LOG()
        LOG("SP: %.6f" % self.measureS.p())
        LOG("SR: %.6f" % self.measureS.r())
        LOG("SF: %.6f" % self.measureS.f())

def score(g_file, s_file, representation):
    representation = representation.lower()
    if representation == "dm":
        LOG("Representation type: DM")
        argument_predicate = argument_predicate_dm
    if representation == "pas":
        LOG("Representation type: PAS")
        argument_predicate = argument_predicate_pas
    if representation == "psd":
        LOG("Representation type: PSD")
        argument_predicate = argument_predicate_psd
        
    LOG("# Evaluation")
    LOG()

    LOG("Gold standard file: %s" % g_file)
    LOG("System output file: %s" % s_file)
    LOG()

    scorer1 = Scorer()
    scorer1.argument_predicate = argument_predicate
    
    scorer2 = Scorer()
    scorer2.argument_predicate = argument_predicate
    
    g_fp = open(g_file)
    s_fp = open(s_file)
    for g, s in zip(read_graphs(g_fp), read_graphs(s_fp)):
        g = make_graph(g)
        s = make_graph(s)
        scorer2.update(g, s)
        g = add_virtual(g)
        s = add_virtual(s)
        scorer1.update(g, s)
    g_fp.close()
    s_fp.close()
    
    LOG("## Scores including virtual dependencies to top nodes")
    LOG()
    scorer1.report()
    LOG()
    
    LOG("## Scores excluding virtual dependencies to top nodes")
    LOG()
    scorer2.report()
    
if __name__ == "__main__":
    representation = "dm"
    for arg in sys.argv[1:]:
        if arg.startswith("representation="):
            representation = arg[15:].lower()
    score(sys.argv[1], sys.argv[2], representation)
