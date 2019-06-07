from score.core import intersect

class InternalGraph():

    def __init__(self, graph):
        self.id2node = dict()
        node2id = dict()
        self.nodes = []
        self.id2edge = dict()
        self.edges = []
        for i, node in enumerate(graph.nodes):
            self.id2node[i] = node
            node2id[node] = i
            self.nodes.append(i)
        for i, edge in enumerate(graph.edges):
            self.id2edge[i] = edge
            src = graph.find_node(edge.src)
            tgt = graph.find_node(edge.tgt)
            self.edges.append(((node2id[src], node2id[tgt]), edge.lab))

def make_edge_correspondence(graph1, graph2, respect_label=True):
    correspondence = dict()
    for raw_edge1 in graph1.edges:
        edge1, lab1 = raw_edge1
        correspondence[edge1] = set()
        for raw_edge2 in graph2.edges:
            edge2, lab2 = raw_edge2
            if not respect_label or lab1 == lab2:
                correspondence[edge1].add(edge2)
    return correspondence

def update_edge_correspondence(edge_correspondence, i, j):
    new_correspondence = dict()
    new_potential = 0
    for edge1 in edge_correspondence:
        src1, tgt1 = edge1
        if src1 != i and tgt1 != i:
            new_correspondence[edge1] = edge_correspondence[edge1]
            new_potential += len(new_correspondence[edge1]) > 0
        else:
            new_correspondence[edge1] = set()
            for edge2 in edge_correspondence[edge1]:
                src2, tgt2 = edge2
                if src1 == i and src2 == j:
                    new_correspondence[edge1].add(edge2)
                if tgt1 == i and tgt2 == j:
                    new_correspondence[edge1].add(edge2)
            new_potential += len(new_correspondence[edge1]) > 0
    return new_correspondence, new_potential

def splits(xs):
    for i, x in enumerate(xs):
        yield x, xs[:i] + xs[i+1:]
    yield -1, xs    # do not assign

def adjacent(graph, i):
    for src, tgt in graph.edges:
        if i == src:
            yield tgt
        if i == tgt:
            yield src

def evaluate_candidate(graph1, graph2, cv, i, j):
    mapped_i_neighbours = set()
    for neighbour in adjacent(graph1, i):
        if neighbour in cv:
            mapped_i_neighbours.add(cv[neighbour])
    j_neighbours = set(adjacent(graph2, j))
    return len(mapped_i_neighbours & j_neighbours)

def sorted_splits(graph1, graph2, cv, i, xs):
    sorted_xs = sorted(xs, key=lambda x: evaluate_candidate(graph1, graph2, cv, i, x), reverse=True)
    yield from splits(sorted_xs)

def correspondences(graph1, graph2):
    graph1 = InternalGraph(graph1)
    graph2 = InternalGraph(graph2)
    cv = dict()
    ce = make_edge_correspondence(graph1, graph2)
    i = 0
    todo = [(cv, ce, i, splits(graph2.nodes))]
    n_matched = 0
    while todo:
        cv, ce, i, untried = todo[-1]
        try:
            j, new_untried = next(untried)
            new_cv = dict(cv)
            new_cv[i] = j
            new_ce, new_potential = update_edge_correspondence(ce, i, j)
            if i < len(graph1.nodes):
                if new_potential > n_matched:
                    todo.append((new_cv, new_ce, i+1, sorted_splits(graph1, graph2, new_cv, i+1, new_untried)))
            else:
                yield new_cv, new_ce
                n_matched = max(n_matched, new_potential)
        except StopIteration:
            todo.pop()

def is_valid(correspondence):
    return all(len(x) <= 1 for x in correspondence.values())

def is_injective(correspondence):
    seen = set()
    for xs in correspondence.values():
        for x in xs:
            if x in seen:
                return False
            else:
                seen.add(x)
    return True

def evaluate(gold, system, stream, format = "json", trace = False):
    counter = 0
    for g, s in intersect(gold, system):
#        if len(s.nodes) > 10:
#            continue
        print("Number of nodes: {}".format(len(g.nodes)))
        print("Number of edges: {}".format(len(g.edges)))
        n_matched = 0
        i = 0
        best_cv, best_ce = None, None
        for cv, ce in correspondences(g, s):
            assert is_valid(ce)
            assert is_injective(ce)
            print("\r{}".format(i), end="")
            n = 0
            for edge1 in ce:
                for edge2 in ce[edge1]:
                    n += 1
            if n > n_matched:
                n_matched = n
                best_cv, best_ce = cv, ce
            i += 1
        print()
        print("Number of edges in correspondence: {}".format(n_matched))
        print(best_cv)
        print(best_ce)
        counter += 1
#        if counter > 5:
#            break
