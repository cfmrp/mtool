# Marco Kuhlmann <marco.kuhlmann@liu.se>

import sys

from score.core import anchor, intersect;

class Measure(object):

    def __init__(self, get_items):
        self.get_items = get_items
        self.g = 0
        self.s = 0
        self.c = 0
        self.n_updates = 0
        self.n_matches = 0

    def update(self, gold, system, gidentities, sidentities, trace = 0):
        g_items = set(self.get_items(gold, gidentities))
        s_items = set(self.get_items(system, sidentities))
        self.g += len(g_items)
        self.s += len(s_items)
        self.c += len(g_items & s_items)
        self.n_updates += 1
        self.n_matches += g_items == s_items
        if trace:
            return {"g": len(g_items), "s": len(s_items),
                    "c": len(g_items & s_items), "m": 1 if g_items == s_items else 0};

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

    def report(self):
        json = {}
        json["g"] = self.g
        json["s"] = self.s
        json["c"] = self.c
        json["p"] = self.p()
        json["r"] = self.r()
        json["f"] = self.f()
        json["m"] = self.m()
        return json

# def argument_predicate_dm(label):
#     return True

# def argument_predicate_pas(label):
#     arguments = set("adj_ARG1 adj_ARG2 adj_MOD coord_ARG1 coord_ARG2 prep_ARG1 prep_ARG2 prep_ARG3 prep_MOD verb_ARG1 verb_ARG2 verb_ARG3 verb_ARG4 verb_MOD".split())
#     return label in arguments

# def argument_predicate_psd(label):
#     return label.endswith("-arg")

class Scorer(object):

    def __init__(self, include_virtual=True):
        self.measures = []
        self.measures.append(("labeled", Measure(self.get_itemsL)))
        self.measures.append(("unlabeled", Measure(self.get_itemsU)))
        # self.measureP = Measure(self.get_itemsP)
        # self.measureF = Measure(self.get_itemsF)
        # self.measureS = Measure(self.get_itemsS)
        self.include_virtual = include_virtual

    def identify(self, id):
        return self.identities[id]
    
    def get_itemsL(self, graph, identities):
        result = {(identities[e.src], identities[e.tgt], e.lab) for e in graph.edges}
        if self.include_virtual:
            for node in graph.nodes:
                if node.is_top:
                    result.add((-1, identities[node.id], None))
        return result

    def get_itemsU(self, graph, identities):
        result = {(identities[e.src], identities[e.tgt]) for e in graph.edges}
        if self.include_virtual:
            for node in graph.nodes:
                if node.is_top:
                    result.add((-1, identities[node.id]))
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

    def update(self, g, s, trace):
        gidentities = {node.id: tuple(anchor(node)) for node in g.nodes}
        sidentities = {node.id: tuple(anchor(node)) for node in s.nodes}
        scores = dict();
        for key, measure in self.measures:
            score = measure.update(g, s, gidentities, sidentities, trace)
            if trace: scores[key] = score;
        return scores;

    def report(self, n, scores = None):
        json = {"n": n}
        for info, measure in self.measures:
            json[info] = measure.report()
        if scores is not None: json["scores"] = scores
        return json

def evaluate(gold, system, format = "json", trace = 0):
    scorer = Scorer(include_virtual=True)
    n = 0
    scores = dict() if trace else None
    for g, s in intersect(gold, system):
        score = scorer.update(g, s, trace)
        n += 1
        if trace: scores[g.id] = score
    result = scorer.report(n, scores)
    return result
