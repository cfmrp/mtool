# Marco Kuhlmann <marco.kuhlmann@liu.se>

import sys

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
        return self.c / self.s if self.s != 0 else 0.0

    def r(self):
        return self.c / self.g if self.g != 0 else 0.0

    def f(self):
        p = self.p()
        r = self.r()
        return 2 * p * r / (p + r) if p + r != 0 else 0.0

    def m(self):
        return self.n_matches / self.n_updates if self.n_updates != 0 else 0.0

# def argument_predicate_dm(label):
#     return True

# def argument_predicate_pas(label):
#     arguments = set("adj_ARG1 adj_ARG2 adj_MOD coord_ARG1 coord_ARG2 prep_ARG1 prep_ARG2 prep_ARG3 prep_MOD verb_ARG1 verb_ARG2 verb_ARG3 verb_ARG4 verb_MOD".split())
#     return label in arguments

# def argument_predicate_psd(label):
#     return label.endswith("-arg")

class Scorer(object):

    def __init__(self, include_virtual=False, stream=sys.stderr):
        self.stream = stream
        self.measureL = Measure(self.get_itemsL)
        self.measureU = Measure(self.get_itemsU)
        # self.measureP = Measure(self.get_itemsP)
        # self.measureF = Measure(self.get_itemsF)
        # self.measureS = Measure(self.get_itemsS)
        self.include_virtual = include_virtual

    def log(self, msg=""):
        print(msg, file=self.stream)

    def get_itemsL(self, graph):
        result = {(e.src, e.tgt, e.lab) for e in graph.edges}
        if self.include_virtual:
            for node in graph.nodes:
                if node.is_top:
                    result.add((-1, node.id, None))
        return result

    def get_itemsU(self, graph):
        result = {(e.src, e.tgt) for e in graph.edges}
        if self.include_virtual:
            for node in graph.nodes:
                if node.is_top:
                    result.add((-1, node.id))
        return result

    # def get_itemsP(self, graph):
    #     return {(frame[0], frame[2]) for frame in self.get_itemsF(graph)}

    # def get_itemsF(self, graph):
    #     result = set()
    #     for node in graph.nodes:
    #         if self.has_scorable_predicate(node):
    #             arguments = set()
    #             for edge in node.outgoing_edges:
    #                 if self.argument_predicate(edge.lab):
    #                     arguments.add(edge)
    #             extract = (node.id, node.sense, tuple(sorted(arguments)))
    #             result.add(extract)
    #     return result

    # def get_itemsS(self, graph):
    #     return {(frame[0], frame[1]) for frame in self.get_itemsF(graph)}

    # def argument_predicate(self, label):
    #     return True

    # def has_scorable_predicate(self, node):
    #     return node.pred and node.pos.startswith("V")

    # def show_predications(self, g):
    #     print(g.id)
    #     report_predications(self.complete_predications(g))

    def update(self, g, s):
        self.measureL.update(g, s)
        self.measureU.update(g, s)
        # self.measureP.update(g, s)
        # self.measureF.update(g, s)
        # self.measureS.update(g, s)

    def report(self):
        self.log("### Labeled scores")
        self.log()
        self.log("Number of edges in gold standard: %d" % self.measureL.g)
        self.log("Number of edges in system output: %d" % self.measureL.s)
        self.log("Number of edges in common: %d" % self.measureL.c)
        self.log()
        self.log("LP: %.6f" % self.measureL.p())
        self.log("LR: %.6f" % self.measureL.r())
        self.log("LF: %.6f" % self.measureL.f())
        self.log("LM: %.6f" % self.measureL.m())
        self.log()

        self.log("### Unlabeled scores")
        self.log()
        self.log("Number of unlabeled edges in gold standard: %d" % self.measureU.g)
        self.log("Number of unlabeled edges in system output: %d" % self.measureU.s)
        self.log("Number of unlabeled edges in common: %d" % self.measureU.c)
        self.log()
        self.log("UP: %.6f" % self.measureU.p())
        self.log("UR: %.6f" % self.measureU.r())
        self.log("UF: %.6f" % self.measureU.f())
        self.log("UM: %.6f" % self.measureU.m())
        self.log()

        # LOG("### Complete predications")
        # LOG()
        # LOG("Number of complete predications in gold standard: %d" % self.measureP.g)
        # LOG("Number of complete predications in system output: %d" % self.measureP.s)
        # LOG("Number of complete predications in common: %d" % self.measureP.c)
        # LOG()
        # LOG("PP: %.6f" % self.measureP.p())
        # LOG("PR: %.6f" % self.measureP.r())
        # LOG("PF: %.6f" % self.measureP.f())
        # LOG()
    
        # LOG("### Semantic frames")
        # LOG()
        # LOG("Number of semantic frames in gold standard: %d" % self.measureF.g)
        # LOG("Number of semantic frames in system output: %d" % self.measureF.s)
        # LOG("Number of semantic frames in common: %d" % self.measureF.c)
        # LOG()
        # LOG("FP: %.6f" % self.measureF.p())
        # LOG("FR: %.6f" % self.measureF.r())
        # LOG("FF: %.6f" % self.measureF.f())
        # LOG()

        # LOG("### Senses")
        # LOG()
        # LOG("Number of senses in gold standard: %d" % self.measureS.g)
        # LOG("Number of senses in system output: %d" % self.measureS.s)
        # LOG("Number of senses in common: %d" % self.measureS.c)
        # LOG()
        # LOG("SP: %.6f" % self.measureS.p())
        # LOG("SR: %.6f" % self.measureS.r())
        # LOG("SF: %.6f" % self.measureS.f())

def evaluate(gold, system, stream, format = "json"):
    scorer1 = Scorer(include_virtual=False)
    scorer2 = Scorer(include_virtual=True)

    for g, s in zip(gold, system):
        scorer1.update(g, s)
        scorer2.update(g, s)

    scorer1.report()
    scorer2.report()
