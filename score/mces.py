import numpy as np
from operator import itemgetter
from graph import Graph
from score.core import fscore, intersect

counter = 0


def reindex(i):
    return -2 - i


def get_or_update(index, key):
    return index.setdefault(key, len(index))


class InternalGraph():

    def __init__(self, graph, index):
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
            src = self.node2id[src]
            tgt = graph.find_node(edge.tgt)
            tgt = self.node2id[tgt]
            self.edges.append((src, tgt, edge.lab))
            if edge.properties:
                for prop, val in zip(edge.properties, edge.values):
                    self.edges.append((src, tgt, ("E", prop, val)))
        #
        # Build the pseudo-edges. These have target nodes that are
        # unique for the value of the label, anchor, property.
        #
        if index is None:
            index = dict()
        for i, node in enumerate(graph.nodes):
            # labels
            j = get_or_update(index, ("L", node.label))
            self.edges.append((i, reindex(j), None))
            # tops
            if node.is_top:
                j = get_or_update(index, ("T"))
                self.edges.append((i, reindex(j), None))
            # anchors
            if node.anchors is not None:
                for anchor in node.anchors:
                    j = get_or_update(index, ("A", anchor["from"], anchor["to"]))
                    self.edges.append((i, reindex(j), None))
            # properties
            if node.properties:
                for prop, val in zip(node.properties, node.values):
                    j = get_or_update(index, ("P", prop, val))
                    self.edges.append((i, reindex(j), None))


def initial_node_correspondences(graph1, graph2):
    #
    # in the following, we assume that nodes in raw and internal
    # graphs correspond by position into the .nodes. list
    #
    rewards = np.zeros((len(graph1.nodes), len(graph2.nodes) + 1),
                       dtype=np.int8);
    edges = np.zeros((len(graph1.nodes), len(graph2.nodes) + 1),
                     dtype=np.int8);
    queue = [];
    for i, node1 in enumerate(graph1.nodes):
        for j, node2 in enumerate(graph2.nodes + [None]):
            rewards[i, j], _, _, _ = node1.compare(node2);
            #
            # also determine the maximum number of edge matches we
            # can hope to score, for each node-node correspondence
            #
            if node2 is not None:
                for edge1 in graph1.edges:
                    for edge2 in graph2.edges:
                        if edge1.src == node1.id \
                           and edge2.src == node2.id \
                           and edge1.lab == edge2.lab:
                            edges[i, j] += 1;
                        if edge1.tgt == node1.id \
                           and edge2.tgt == node2.id \
                           and edge1.lab == edge2.lab:
                            edges[i, j] += 1;
            queue.append((rewards[i, j], edges[i, j],
                          i, j if node2 is not None else None));
    if False:
        pairs = [];
        sources = set();
        targets = set();
        for _, _, i, j in sorted(queue, key = itemgetter(0, 1), reverse = True):
            if i not in sources and j not in targets:
                pairs.append((i, j));
                sources.add(i);
                if j is not None: targets.add(j);
        #
        # adjust rewards to use edge potential as a secondary key; maybe
        # we should rather pass around edges and adjust sorted_slits()?
        #
        for i in range(rewards.shape[0]):
            for j in range(rewards.shape[1]):
                rewards[i, j] = 10 * rewards[i, j] + edges[i, j];
#        print(rewards)
#        print(pairs)
        return pairs, rewards;
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


# The next function constructs the initial table with the candidates
# for the edge-to-edge correspondence. Each edge in the source graph
# is mapped to the set of all edges in the target graph.

def make_edge_candidates(graph1, graph2):
    candidates = dict()
    for raw_edge1 in graph1.edges:
        src1, tgt1, lab1 = raw_edge1
        edge1 = src1, tgt1
        candidates[edge1] = set()
        for raw_edge2 in graph2.edges:
            src2, tgt2, lab2 = raw_edge2
            edge2 = src2, tgt2
            if tgt1 < 0:
                # Edge edge1 is a pseudoedge. This can only map to
                # another pseudoedge pointing to the same pseudonode.
                if tgt2 == tgt1 and lab1 == lab2:
                    candidates[edge1].add(edge2)
            else:
                # Edge edge1 is a real edge. This can only map to
                # another real edge.
                if tgt2 >= 0 and lab1 == lab2:
                    candidates[edge1].add(edge2)
    return candidates


# The next function updates the table with the candidates for the
# edge-to-edge correspondence when node `i` is tentatively mapped to
# node `j`.

def update_edge_candidates(edge_candidates, i, j):
    new_candidates = dict()
    new_potential = 0
    for edge1 in edge_candidates:
        src1, tgt1 = edge1
        if src1 != i and tgt1 != i:
            # Edge edge1 is not affected by the tentative
            # assignment. Just include a pointer to the candidates for
            # edge1 in the old assignment.
            new_candidates[edge1] = edge_candidates[edge1]
        else:
            # Edge edge1 is affected by the tentative assignment. Need
            # to explicitly construct the new set of candidates for
            # edge1.
            new_candidates[edge1] = set()
            for edge2 in edge_candidates[edge1]:
                src2, tgt2 = edge2
                if src1 == i and src2 == j:
                    # Both edges share the same source node (modulo
                    # the tentative assignment).
                    new_candidates[edge1].add(edge2)
                if tgt1 == i and tgt2 == j:
                    # Both edges share the same target node (modulo
                    # the tentative assignment).
                    new_candidates[edge1].add(edge2)
        new_potential += len(new_candidates[edge1]) > 0
    return new_candidates, new_potential


def splits(xs):
    # The source graph node is mapped to some target graph node (x).
    for i, x in enumerate(xs):
        yield x, xs[:i] + xs[i+1:]
    # The source graph node is not mapped to any target graph node.
    yield -1, xs


def sorted_splits(i, xs, rewards):
    sorted_xs = sorted(xs, key=lambda x: rewards[i][x], reverse=True)
    yield from splits(sorted_xs)


# Find all maximum edge correspondences between the source graph
# (graph1) and the target graph (graph2). This implements the
# algorithm of McGregor (1982).

def correspondences(graph1, graph2, pairs, rewards, limit=0, trace=0):
    global counter
    bilexical = graph1.flavor == 0 and graph2.flavor == 0
    index = dict()
    graph1 = InternalGraph(graph1, index)
    graph2 = InternalGraph(graph2, index)
    cv = dict()
    ce = make_edge_candidates(graph1, graph2)
    # Visit the source graph nodes in descending order of rewards.
    source_todo = [pair[0] for pair in pairs]
    todo = [(cv, ce, source_todo, sorted_splits(
        source_todo[0], graph2.nodes, rewards))]
    n_matched = 0
    while todo and (limit == 0 or counter <= limit):
        cv, ce, source_todo, untried = todo[-1]
        i = source_todo[0]
        try:
            j, new_untried = next(untried)
            if bilexical and cv:
                min_j = max(_j for _i, _j in cv.items() if _i < i) + 1
                if j < min_j:
                    continue
            counter += 1
            if trace > 2: print("({}:{}) ".format(i, j), end="")
            new_cv = dict(cv)
            new_cv[i] = j
            new_ce, new_potential = update_edge_candidates(ce, i, j)
            if new_potential > n_matched:
                new_source_todo = source_todo[1:]
                if new_source_todo:
                    if trace > 2: print("> ", end="")
                    todo.append((new_cv, new_ce, new_source_todo, sorted_splits(
                        new_source_todo[0], new_untried, rewards)))
                else:
                    if trace > 2: print()
                    yield new_cv, new_ce
                    n_matched = new_potential
        except StopIteration:
            if trace > 2: print("< ")
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


def evaluate(gold, system, format="json", limit=500000, trace=0):

    global counter;

    def update(total, counts):
        for key in ("g", "s", "c"):
            total[key] += counts[key];

    def finalize(counts):
        p, r, f = fscore(counts["g"], counts["s"], counts["c"]);
        counts.update({"p": p, "r": r, "f": f});

    if not limit: limit = 500000;
        
    total_matches = total_steps = 0;
    total_pairs = 0;
    total_tops = {"g": 0, "s": 0, "c": 0}
    total_labels = {"g": 0, "s": 0, "c": 0}
    total_properties = {"g": 0, "s": 0, "c": 0}
    total_anchors = {"g": 0, "s": 0, "c": 0}
    total_edges = {"g": 0, "s": 0, "c": 0}
    scores = dict() if trace else None
    for g, s in intersect(gold, system):
        counter = 0
        pairs, rewards = initial_node_correspondences(g, s)
        if trace > 1:
            print("\n\ngraph #{}".format(g.id))
            print("Number of gold nodes: {}".format(len(g.nodes)))
            print("Number of system nodes: {}".format(len(s.nodes)))
            print("Number of edges: {}".format(len(g.edges)))
            if trace > 2:
                print("Rewards and Pairs:\n{}\n{}\n".format(rewards, pairs))
        n_matched = 0
        i = 0
        best_cv, best_ce = None, None
        for cv, ce in correspondences(g, s, pairs, rewards, limit, trace):
            assert is_valid(ce)
            assert is_injective(ce)
            n = 0
            for edge1 in ce:
                for edge2 in ce[edge1]:
                    n += 1
            if n > n_matched:
                if trace > 1:
                    print("\n[{}] solution #{}; matches: {}".format(counter, i, n));
                n_matched = n
                best_cv, best_ce = cv, ce
            i += 1
        total_matches += n_matched;
        total_steps += counter;
        tops, labels, properties, anchors, edges = g.score(s, best_cv);
        if trace:
            if g.id in scores:
                print("mces.evaluate(): duplicate graph identifier: {}"
                      "".format(gid), file = sys.stderr);
            scores[g.id] = {"tops": tops, "labels": labels,
                            "properties": properties, "anchors": anchors,
                            "edges": edges};
        update(total_tops, tops);
        update(total_labels, labels);
        update(total_properties, properties);
        update(total_anchors, anchors);
        update(total_edges, edges);
        total_pairs += 1;
        if trace > 1:
            print("[{}] Number of edges in correspondence: {}".format(counter, n_matched))
            print("[{}] Total matches: {}".format(total_steps, total_matches));
            print("tops: {}\nlabels: {}\nproperties: {}\nanchors: {}\nedges: {}"
                  "".format(tops, labels, properties, anchors, edges));
            if trace > 2:
                print(best_cv)
                print(best_ce)

    total_all = {"g": 0, "s": 0, "c": 0};
    for counts in [total_tops, total_labels, total_properties, total_anchors, total_edges]:
        update(total_all, counts);
        finalize(counts);
    finalize(total_all);
    result = {"n": total_pairs,
              "tops": total_tops, "labels": total_labels,
              "properties": total_properties,
              "anchors": total_anchors, "edges": total_edges,
              "all": total_all};
    if trace: result["scores"] = scores;
    return result;
