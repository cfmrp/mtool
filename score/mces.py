import multiprocessing as mp
import sys
from operator import itemgetter

import numpy as np

import score.core
from score.smatch import smatch
from score.ucca import identify

counter = 0

def reindex(i):
    return -2 - i

def get_or_update(index, key):
    return index.setdefault(key, len(index))

class InternalGraph():

    def __init__(self, graph, index):
        self.node2id = dict()
        self.id2node = dict()
        self.nodes = []
        self.edges = []
        for i, node in enumerate(graph.nodes):
            self.node2id[node] = i
            self.id2node[i] = node
            self.nodes.append(i)
        for edge in graph.edges:
            src = graph.find_node(edge.src)
            src = self.node2id[src]
            tgt = graph.find_node(edge.tgt)
            tgt = self.node2id[tgt]
            self.edges.append((src, tgt, edge.lab))
            if edge.attributes:
                for prop, val in zip(edge.attributes, edge.values):
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
                anchor = score.core.anchor(node);
                if graph.input:
                    anchor = score.core.explode(graph.input, anchor)
                j = get_or_update(index, ("A", anchor))
                self.edges.append((i, reindex(j), None))
            # properties
            if node.properties:
                for prop, val in zip(node.properties, node.values):
                    j = get_or_update(index, ("P", prop, val))
                    self.edges.append((i, reindex(j), None))

def initial_node_correspondences(graph1, graph2,
                                 identities1, identities2,
                                 bilexical):
    #
    # in the following, we assume that nodes in raw and internal
    # graphs correspond by position into the .nodes. list
    #
    shape = (len(graph1.nodes), len(graph2.nodes) + 1)
    rewards = np.zeros(shape, dtype=np.int);
    edges = np.zeros(shape, dtype=np.int);
    anchors = np.zeros(shape, dtype=np.int);

    #
    # initialization needs to be sensitive to whether or not we are looking at
    # ordered graphs (aka Flavor 0, or the SDP family)
    #
    if bilexical:
        queue = None;
    else:
        queue = [];
        
    for i, node1 in enumerate(graph1.nodes):
        for j, node2 in enumerate(graph2.nodes + [None]):
            rewards[i, j], _, _, _ = node1.compare(node2);
            if node2 is not None:
                #
                # also determine the maximum number of edge matches we
                # can hope to score, for each node-node correspondence
                #
                src_edges_x = [ len([ 1 for e1 in graph1.edges if e1.src == node1.id and e1.lab == e2.lab ])
                                for e2 in graph2.edges if e2.src == node2.id ]
                tgt_edges_x = [ len([ 1 for e1 in graph1.edges if e1.tgt == node1.id and e1.lab == e2.lab ])
                                for e2 in graph2.edges if e2.tgt == node2.id ]
                edges[i, j] += sum(src_edges_x) + sum(tgt_edges_x)

                #
                # and the overlap of UCCA yields (sets of character position)
                #
                if identities1 and identities2:
                    anchors[i, j] += len(identities1[node1.id] &
                                         identities2[node2.id])
            if queue is not None:
                queue.append((rewards[i, j], edges[i, j], anchors[i, j],
                              i, j if node2 is not None else None));

    #
    # adjust rewards to use anchor overlap and edge potential as a secondary
    # and tertiary key, respectively.  for even better initialization, maybe
    # consider edge attributes too?
    #
    rewards *= 1000;
    anchors *= 10;
    rewards += edges + anchors;

    if queue is None:        
        pairs = levenshtein(graph1, graph2);
    else:
        pairs = [];
        sources = set();
        targets = set();
        for _, _, _, i, j in sorted(queue, key = itemgetter(0, 2, 1),
                                    reverse = True):
            if i not in sources and j not in targets:
                pairs.append((i, j));
                sources.add(i);
                if j is not None: targets.add(j);

    return pairs, rewards;

def levenshtein(graph1, graph2):
    m = len(graph1.nodes)
    n = len(graph2.nodes)
    d = {(i,j): float('-inf') for i in range(m+1) for j in range(n+1)}
    p = {(i,j): None for i in range(m+1) for j in range(n+1)}
    d[(0,0)] = 0
    for i in range(1, m+1):
        d[(i,0)] = 0
        p[(i,0)] = ((i-1,0), None)
    for j in range(1, n+1):
        d[(0,j)] = 0
        p[(0,j)] = ((0,j-1), None)
    for j, node2 in enumerate(graph2.nodes, 1):
        for i, node1 in enumerate(graph1.nodes, 1):
            best_d = float('-inf')
            # "deletion"
            cand_d = d[(i-1,j-0)]
            if cand_d > best_d:
                best_d = cand_d
                best_p = ((i-1,j-0), None)
            # "insertion"
            cand_d = d[(i-0,j-1)]
            if cand_d > best_d:
                best_d = cand_d
                best_p = ((i-0,j-1), None)
            # "alignment"
            cand_d = d[(i-1,j-1)] + node1.compare(node2)[2]
            if cand_d > best_d:
                best_d = cand_d
                best_p = ((i-1,j-1), (i-1, j-1))
            d[(i,j)] = best_d
            p[(i,j)] = best_p

    pairs = {i: None for i in range(len(graph1.nodes))}
    def backtrace(idx):
        ptr = p[idx]
        if ptr is None:
            pass
        else:
            next_idx, pair = ptr
            if pair is not None:
                i, j = pair
                pairs[i] = j
            backtrace(next_idx)
    backtrace((m, n))
    return sorted(pairs.items())

# The next function constructs the initial table with the candidates
# for the edge-to-edge correspondence. Each edge in the source graph
# is mapped to the set of all edges in the target graph.
def make_edge_candidates(graph1, graph2):
    candidates = dict()
    for raw_edge1 in graph1.edges:
        src1, tgt1, lab1 = raw_edge1
        if raw_edge1 not in candidates:
            edge1_candidates = set()
        else:
            edge1_candidates = candidates[raw_edge1]
        for raw_edge2 in graph2.edges:
            src2, tgt2, lab2 = raw_edge2
            edge2 = (src2, tgt2)
            if tgt1 < 0:
                # Edge edge1 is a pseudoedge. This can only map to
                # another pseudoedge pointing to the same pseudonode.
                if tgt2 == tgt1 and lab1 == lab2:
                    edge1_candidates.add(edge2)
            elif tgt2 >= 0 and lab1 == lab2:
                # Edge edge1 is a real edge. This can only map to
                # another real edge.
                edge1_candidates.add(edge2)
        if edge1_candidates:
            candidates[raw_edge1] = edge1_candidates
    return candidates

# The next function updates the table with the candidates for the
# edge-to-edge correspondence when node `i` is tentatively mapped to
# node `j`.
def update_edge_candidates(edge_candidates, i, j):
    new_candidates = edge_candidates.copy()
    for edge1, edge1_candidates in edge_candidates.items():
        if i == edge1[0] or i == edge1[1]:
            # Edge edge1 is affected by the tentative assignment. Need
            # to explicitly construct the new set of candidates for
            # edge1.
            # Both edges share the same source/target node
            # (modulo the tentative assignment).
            src1, tgt1, _ = edge1
            edge1_candidates = {(src2, tgt2) for src2, tgt2 in edge1_candidates
                                    if src1 == i and src2 == j or tgt1 == i and tgt2 == j}
            if  edge1_candidates:
                new_candidates[edge1] = edge1_candidates
            else:
                new_candidates.pop(edge1)
    return new_candidates, len(new_candidates)

def splits(xs):
    # The source graph node is mapped to some target graph node (x).
    for i, x in enumerate(xs):
        yield x, xs[:i] + xs[i+1:]
    # The source graph node is not mapped to any target graph node.
    yield -1, xs

def sorted_splits(i, xs, rewards, pairs, bilexical):
    for _i, _j in pairs:
        if i == _i: j = _j if _j is not None else -1
    if bilexical:
        sorted_xs = sorted(xs, key=lambda x: (-abs(x-i), rewards.item((i, x)), -x), reverse=True)
    else:
        sorted_xs = sorted(xs, key=lambda x: (rewards.item((i, x)), -x), reverse=True)
    if j in sorted_xs or j < 0:
        if j >= 0: sorted_xs.remove(j)
        sorted_xs = [j] + sorted_xs
    yield from splits(sorted_xs)

# UCCA-specific rule:
# Do not pursue correspondences of nodes i and j in case there is
# a node dominated by i whose correspondence is not dominated by j
def identities(g, s):
    #
    # use overlap of UCCA yields in picking initial node pairing
    #
    if g.framework == "ucca" and g.input \
            and s.framework == "ucca" and s.input:
        g_identities = dict()
        s_identities = dict()
        g_dominated = dict()
        s_dominated = dict()
        for node in g.nodes:
            g_identities, g_dominated = \
                identify(g, node.id, g_identities, g_dominated)
        g_identities = {key: score.core.explode(g.input, value)
                        for key, value in g_identities.items()}
        for node in s.nodes:
            s_identities, s_dominated = \
                identify(s, node.id, s_identities, s_dominated)
        s_identities = {key: score.core.explode(s.input, value)
                        for key, value in s_identities.items()}
    else:
        g_identities = s_identities = g_dominated = s_dominated = None
    return g_identities, s_identities, g_dominated, s_dominated

def domination_conflict(graph1, graph2, cv, i, j, dominated1, dominated2):
    if not dominated1 or not dominated2 or i < 0 or j < 0:
        return False
    dominated_i = dominated1[graph1.id2node[i].id]
    dominated_j = dominated2[graph2.id2node[j].id]
    # Both must be leaves or both must be non-leaves
    if bool(dominated_i) != bool(dominated_j):
        return True
    for _i, _j in cv.items():
        if _i >= 0 and _j >= 0 and \
                graph1.id2node[_i].id in dominated_i and \
                graph2.id2node[_j].id not in dominated_j:
            return True
    return False

# Find all maximum edge correspondences between the source graph
# (graph1) and the target graph (graph2). This implements the
# algorithm of McGregor (1982).
def correspondences(graph1, graph2, pairs, rewards, limit=None, trace=0,
                    dominated1=None, dominated2=None, bilexical = False):
    global counter
    index = dict()
    graph1 = InternalGraph(graph1, index)
    graph2 = InternalGraph(graph2, index)
    cv = dict()
    ce = make_edge_candidates(graph1, graph2)
    # Visit the source graph nodes in descending order of rewards.
    source_todo = [pair[0] for pair in pairs]
    todo = [(cv, ce, source_todo, sorted_splits(
        source_todo[0], graph2.nodes, rewards, pairs, bilexical))]
    n_matched = 0
    while todo and (limit is None or counter <= limit):
        cv, ce, source_todo, untried = todo[-1]
        i = source_todo[0]
        try:
            j, new_untried = next(untried)
            if cv:
                if bilexical:  # respect node ordering in bi-lexical graphs
                    max_j = max((_j for _i, _j in cv.items() if _i < i), default=-1)
                    if 0 <= j < max_j + 1:
                        continue
                elif domination_conflict(graph1, graph2, cv, i, j, dominated1, dominated2):
                    continue
            counter += 1
            if trace > 2: print("({}:{}) ".format(i, j), end="", file = sys.stderr)
            new_cv = dict(cv)
            new_cv[i] = j
            new_ce, new_potential = update_edge_candidates(ce, i, j)
            if new_potential > n_matched:
                new_source_todo = source_todo[1:]
                if new_source_todo:
                    if trace > 2: print("> ", end="", file = sys.stderr)
                    todo.append((new_cv, new_ce, new_source_todo,
                                 sorted_splits(new_source_todo[0],
                                               new_untried, rewards,
                                               pairs, bilexical)))
                else:
                    if trace > 2: print(file = sys.stderr)
                    yield new_cv, new_ce
                    n_matched = new_potential
        except StopIteration:
            if trace > 2: print("< ", file = sys.stderr)
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

def schedule(g, s, rrhc_limit, mces_limit, trace, errors):
    global counter;
    try:
        counter = 0;
        g_identities, s_identities, g_dominated, s_dominated \
            = identities(g, s);
        bilexical = g.flavor == 0 or g.framework in {"dm", "psd", "pas", "ccd"};
        pairs, rewards \
            = initial_node_correspondences(g, s,
                                           g_identities, s_identities,
                                           bilexical);
        if errors is not None and g.framework not in errors: errors[g.framework] = dict();
        if trace > 1:
            print("\n\ngraph #{} ({}; {})".format(g.id, g.flavor, g.framework),
                  file = sys.stderr);
            print("number of gold nodes: {}".format(len(g.nodes)),
                  file = sys.stderr);
            print("number of system nodes: {}".format(len(s.nodes)),
                  file = sys.stderr);
            print("number of edges: {}".format(len(g.edges)),
                  file = sys.stderr);
            if trace > 2:
                print("rewards and pairs:\n{}\n{}\n"
                      "".format(rewards, sorted(pairs)),
                      file = sys.stderr);
        smatches = 0;
        if g.framework in {"eds", "amr"} and rrhc_limit > 0:
            smatches, _, _, mapping \
                = smatch(g, s, rrhc_limit,
                         {"tops", "labels", "properties", "anchors",
                          "edges", "attributes"},
                         0, False);
            mapping = [(i, j if j >= 0 else None)
                       for i, j in enumerate(mapping)];
            tops, labels, properties, anchors, edges, attributes \
                = g.score(s, mapping);
            all = tops["c"] + labels["c"] + properties["c"] \
                + anchors["c"] + edges["c"] + attributes["c"];
            status = "{}".format(smatches);
            if smatches > all:
                status = "{} vs. {}".format(smatches, all);
                smatches = all;
            if trace > 1:
                print("pairs {} smatch [{}]: {}"
                      "".format("from" if set(pairs) != set(mapping) else "by",
                                status, sorted(mapping)),
                      file = sys.stderr);
            if set(pairs) != set(mapping): pairs = mapping;
        matches, best_cv, best_ce = 0, {}, {};
        if g.nodes and mces_limit > 0:
            for i, (cv, ce) in \
                enumerate(correspondences(g, s, pairs, rewards,
                                          mces_limit, trace,
                                          dominated1 = g_dominated,
                                          dominated2 = s_dominated,
                                          bilexical = bilexical)):
#               assert is_valid(ce)
#               assert is_injective(ce)
                n = sum(map(len, ce.values()));
                if n > matches:
                    if trace > 1:
                        print("\n[{}] solution #{}; matches: {}"
                              "".format(counter, i, n), file = sys.stderr);
                    matches, best_cv, best_ce = n, cv, ce;
        tops, labels, properties, anchors, edges, attributes \
            = g.score(s, best_cv or pairs, errors);
#       assert matches >= smatches;
        if trace > 1:
            if smatches and matches != smatches:
                print("delta to smatch: {}"
                      "".format(matches - smatches), file = sys.stderr);
            print("[{}] edges in correspondence: {}"
                  "".format(counter, matches), file = sys.stderr)
            print("tops: {}\nlabels: {}\nproperties: {}\nanchors: {}"
                  "\nedges: {}\nattributes: {}"
                  "".format(tops, labels, properties, anchors,
                            edges, attributes), file = sys.stderr);
            if trace > 2:
                print(best_cv, file = sys.stderr)
                print(best_ce, file = sys.stderr)
        return g.id, g, s, tops, labels, properties, anchors, \
            edges, attributes, matches, counter, None;
                
    except Exception as e:
        #
        # _fix_me_
        #
        raise e;
        return g.id, g, s, None, None, None, None, None, None, None, None, e;

def evaluate(gold, system, format = "json",
             limits = None,
             cores = 0, trace = 0, errors = None, quiet = False):
    def update(total, counts):
        for key in ("g", "s", "c"):
            total[key] += counts[key];

    def finalize(counts):
        p, r, f = score.core.fscore(counts["g"], counts["s"], counts["c"]);
        counts.update({"p": p, "r": r, "f": f});

    if limits is None:
        limits = {"rrhc": 20, "mces": 500000}
    rrhc_limit = mces_limit = None;
    if isinstance(limits, dict):
        if "rrhc" in limits: rrhc_limit = limits["rrhc"];
        if "mces" in limits: mces_limit = limits["mces"];
    if rrhc_limit is None or rrhc_limit < 0: rrhc_limit = 20;
    if mces_limit is None or mces_limit < 0: mces_limit = 500000;
    if trace > 1:
        print("RRHC limit: {}; MCES limit: {}".format(rrhc_limit, mces_limit),
              file = sys.stderr);
    total_matches = total_steps = 0;
    total_pairs = 0;
    total_empty = 0;
    total_inexact = 0;
    total_tops = {"g": 0, "s": 0, "c": 0}
    total_labels = {"g": 0, "s": 0, "c": 0}
    total_properties = {"g": 0, "s": 0, "c": 0}
    total_anchors = {"g": 0, "s": 0, "c": 0}
    total_edges = {"g": 0, "s": 0, "c": 0}
    total_attributes = {"g": 0, "s": 0, "c": 0}
    scores = dict() if trace else None;
    if cores > 1:
        if trace > 1:
            print("mces.evaluate(): using {} cores".format(cores),
                  file = sys.stderr);
        with mp.Pool(cores) as pool:
            results = pool.starmap(schedule,
                                   ((g, s, rrhc_limit, mces_limit,
                                     trace, errors)
                                    for g, s
                                    in score.core.intersect(gold,
                                                            system,
                                                            quiet = quiet)));
    else:
        results = (schedule(g, s, rrhc_limit, mces_limit, trace, errors)
                   for g, s in score.core.intersect(gold, system));

    for id, g, s, tops, labels, properties, anchors, \
        edges, attributes, matches, steps, error \
        in results:
        framework = g.framework if g.framework else "none";
        if scores is not None and framework not in scores: scores[framework] = dict();
        if s.nodes is None or len(s.nodes) == 0:
            total_empty += 1;
        if error is None:
            total_matches += matches;
            total_steps += steps;
            update(total_tops, tops);
            update(total_labels, labels);
            update(total_properties, properties);
            update(total_anchors, anchors);
            update(total_edges, edges);
            update(total_attributes, attributes);
            total_pairs += 1;
            if mces_limit == 0 or steps > mces_limit: total_inexact += 1;

            if trace and s.nodes is not None and len(s.nodes) != 0:
                if id in scores[framework]:
                    print("mces.evaluate(): duplicate {} graph identifier: {}"
                          "".format(framework, id), file = sys.stderr);
                scores[framework][id] \
                    = {"tops": tops, "labels": labels,
                       "properties": properties, "anchors": anchors,
                       "edges": edges, "attributes": attributes,
                       "exact": not (mces_limit == 0 or steps > mces_limit),
                       "steps": steps};
        else:
            print("mces.evaluate(): exception in {} graph #{}:\n{}"
                  "".format(framework, id, error));
            if trace:
                scores[framework][id] = {"error": repr(error)};

    total_all = {"g": 0, "s": 0, "c": 0};
    for counts in [total_tops, total_labels, total_properties, total_anchors,
                   total_edges, total_attributes]:
        update(total_all, counts);
        finalize(counts);
    finalize(total_all);
    result = {"n": total_pairs, "null": total_empty,
              "exact": total_pairs - total_inexact,
              "tops": total_tops, "labels": total_labels,
              "properties": total_properties, "anchors": total_anchors,
              "edges": total_edges, "attributes": total_attributes,
              "all": total_all};
    if trace: result["scores"] = scores;
    return result;
