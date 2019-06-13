import numpy as np;

from graph import Graph;
from score.core import intersect

def reindex(i):
    return -2 - i

def get_or_update(index, key):
    return index.setdefault(key, len(index))

class InternalGraph():

    def __init__(self, graph, index=None):
        self.id2node = dict()
        self.node2id = dict()
        self.nodes = []
        self.id2edge = dict()
        self.edges = []
        for i, node in enumerate(graph.nodes):
            self.id2node[i] = node
            self.node2id[node] = i
            self.nodes.append(i)
        for i, edge in enumerate(graph.edges):
            self.id2edge[i] = edge
            src = graph.find_node(edge.src)
            tgt = graph.find_node(edge.tgt)
            self.edges.append((self.node2id[src], self.node2id[tgt]))
        #
        # Build the pseudo-edges. These have target nodes that are
        # unique for the value of the label, anchor, property.
        #
        if index is None:
            index = dict()
        for i, node in enumerate(graph.nodes):
            # labels
            j = get_or_update(index, node.label)
            self.edges.append((i, reindex(j)))
            # anchors
            for anchor in node.anchors:
                j = get_or_update(index, "{from}:{to}".format(**anchor))
                self.edges.append((i, reindex(j)))
            # properties
            if node.properties:
                for prop, val in zip(node.properties, node.values):
                    j = get_or_update(index, prop + "=" + val)
                    self.edges.append((i, reindex(j)))

    def map_node(self, node):
        return self.node2id(node);

    def unmap_node(self, id):
        return self.id2node(id);


def initial_match_making(graph1, graph2):
    #
    # in the following, we assume that nodes in raw and internal
    # graphs correspond by position into the .nodes. list
    #
    rewards = np.zeros((len(graph1.nodes), len(graph2.nodes) + 1),
                       dtype = np.int8);
    for i, node1 in enumerate(graph1.nodes):
        for j, node2 in enumerate(graph2.nodes + [None]):
            rewards[i, j], _, _, _ = node1.compare(node2);
    pairs = [];
    used = set();
    bottom = rewards.min() - 1;
    top = rewards.max();
    copy = np.array(rewards);
    while top > bottom:
        i, j = np.unravel_index(copy.argmax(), copy.shape);
        copy[i] = bottom;
        copy[:, j] = bottom;
        pairs.append((i, j if j < len(graph2.nodes) else None));
        used.add(i);
        top = copy.max();
    for i in range(len(graph1.nodes)):
        if i not in used:
            pairs.append((i, None));
            used.add(i);
    return pairs, rewards;

def make_edge_correspondence(graph1, graph2):
    correspondence = dict()
    for edge1 in graph1.edges:
        src1, tgt1 = edge1
        correspondence[edge1] = set()
        for edge2 in graph2.edges:
            src2, tgt2 = edge2
            if tgt1 < 0:
                # Pseudoedges can correspond to each other only if
                # they point to the same pseudonode.
                if tgt2 == tgt1:
                    correspondence[edge1].add(edge2)
            else:
                # Real edge. Check that the other edge also is real.
                if tgt2 >= 0:
                    correspondence[edge1].add(edge2)
    return correspondence

def make_edge_correspondence_new(graph1, graph2):
    correspondence = dict()
    for edge1 in graph1.edges:
        src1, tgt1 = edge1
        correspondence[edge1] = set()
        if tgt1 >= 0:
            for edge2 in graph2.edges:
                correspondence[edge1].add(edge2)
        else:
            for src2, tgt2 in graph2.edges:
                if tgt2 == tgt1:
                    correspondence[edge1].add(edge2)
    return correspondence

def update_edge_correspondence_old(cv, edge_correspondence, i, j):
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
                if src1 == i and src2 == j and (tgt1 not in cv or tgt2 == cv[tgt1]):
                    new_correspondence[edge1].add(edge2)
                if tgt1 == i and tgt2 == j and (src1 not in cv or src2 == cv[src1]):
                    new_correspondence[edge1].add(edge2)
            new_potential += len(new_correspondence[edge1]) > 0
    return new_correspondence, new_potential

def update_edge_correspondence(cv, edge_correspondence, i, j):
    new_correspondence = dict()
    new_potential = 0
    for edge1 in edge_correspondence:
        src1, tgt1 = edge1
        if src1 != i and tgt1 != i:
            new_correspondence[edge1] = edge_correspondence[edge1]
            # new_correspondence[edge1] = set()
            # for edge2 in edge_correspondence[edge1]:
            #     src2, tgt2 = edge2
            #     if (src1 not in cv or cv[src1] == src2) and (tgt1 not in cv or cv[tgt1] == tgt2):
            #         new_correspondence[edge1].add(edge2)
            new_potential += len(new_correspondence[edge1]) > 0
        else:
            new_correspondence[edge1] = set()
            for edge2 in edge_correspondence[edge1]:
                src2, tgt2 = edge2
                if src1 == i and src2 == j: # and (tgt1 not in cv or tgt2 == cv[tgt1]):
                    new_correspondence[edge1].add(edge2)
                if tgt1 == i and tgt2 == j: # and (src1 not in cv or src2 == cv[src1]):
                    new_correspondence[edge1].add(edge2)
            new_potential += len(new_correspondence[edge1]) > 0
    return new_correspondence, new_potential

def splits(xs):
    # The source graph node is mapped to some target graph node (x).
    for i, x in enumerate(xs):
        yield x, xs[:i] + xs[i+1:]
    # The source graph node is not mapped to any target graph node.
    yield -1, xs

def guided_splits(source, nodes, pairs):
    match = None;
    for node1, node2 in pairs:
        if node1 == source: match = node2;
    if match is not None:
        i = nodes.index(match);
        yield match, nodes[:i] + nodes[i + 1:];
    for i, node in enumerate(nodes):
        if node is not match:
            yield node, nodes[:i] + nodes[i + 1:];
    yield -1, nodes;

def sorted_splits(i, xs, rewards):
    sorted_xs = sorted(xs, key=lambda x: rewards[i][x], reverse=True)
    yield from splits(sorted_xs)

def correspondences(graph1, graph2, pairs, rewards):
    index = dict()
    graph1 = InternalGraph(graph1, index)
    graph2 = InternalGraph(graph2, index)
    cv = dict()
    ce = make_edge_correspondence(graph1, graph2)
    # Visit the source graph nodes in descending order of rewards.
#    source_todo = sorted(graph1.nodes, key=lambda i: sum(rewards[i]), reverse=True)
    source_todo = [pair[0] for pair in pairs];
#    todo = [(cv, ce, graph1.nodes, splits(graph2.nodes))]
    todo = [(cv, ce, source_todo, sorted_splits(source_todo[0], graph2.nodes, rewards))]
#    todo = [(cv, ce, source_todo, guided_splits(source_todo[0], graph2.nodes, pairs))]
    n_matched = 0
    while todo:
        cv, ce, source_todo, untried = todo[-1]
        i = source_todo[0]
        try:
            j, new_untried = next(untried)
#            print(" ({}:{})".format(i, j), end="");
            new_cv = dict(cv)
            new_cv[i] = j
            new_ce, new_potential = update_edge_correspondence(cv, ce, i, j)
            if new_potential > n_matched:
                # Which source graph nodes i could make a difference, in
                # the sense that assigning them could change the edge
                # correspondence? (Not sure whether this actually helps.)
                relevant = set()
                for edge1 in new_ce:
                    if new_ce[edge1]:
                        src1, tgt1 = edge1
                        if src1 not in cv:
                            assert src1 >= 0
                            relevant.add(src1)
                        if tgt1 not in cv and tgt1 >= 0:
                            relevant.add(tgt1)
                new_source_todo = []
                for new_i in source_todo[1:]:
                    if new_i in relevant:
                        new_source_todo.append(new_i)
                source_todo = new_source_todo
                # End "optimization" here
                if new_source_todo:
                    todo.append((new_cv, new_ce, new_source_todo, sorted_splits(new_source_todo[0], new_untried, rewards)))
                else:
                    yield new_cv, new_ce
                    n_matched = new_potential
        except StopIteration:
#            print();
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
        print("Number of gold nodes: {}".format(len(g.nodes)))
        print("Number of system nodes: {}".format(len(s.nodes)))
        print("Number of edges: {}".format(len(g.edges)))
        pairs, rewards = initial_match_making(g, s);
        print("{}\n{}\n".format(rewards, pairs));
        n_matched = 0
        i = 0
        best_cv, best_ce = None, None
        for cv, ce in correspondences(g, s, pairs, rewards):
            assert is_valid(ce)
            assert is_injective(ce)
            n = 0
            for edge1 in ce:
                for edge2 in ce[edge1]:
                    n += 1
            if n > n_matched:
                print("\nsolution #{}; matches: {}".format(i, n));
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
