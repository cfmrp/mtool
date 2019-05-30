import collections
import sys

def make_clique(graph, nodes):
    for v1 in nodes:
        for v2 in nodes:
            if v1 != v2:
                graph[v1].add(v2)

def count_fillin(graph, nodes):
    """How many edges would be needed to make v a clique."""
    count = 0
    for v1 in nodes:
        for v2 in nodes:
            if v1 != v2 and v2 not in graph[v1]:
                count += 1
    return count/2

def is_clique(graph, vs):
    for v1 in vs:
        for v2 in vs:
            if v1 != v2 and v2 not in graph[v1]:
                return False
    return True

def simplicial(graph, v):
    return is_clique(graph, graph[v])

def almost_simplicial(graph, v):
    for u in graph[v]:
        if is_clique(graph, graph[v] - {u}):
            return True
    return False

def eliminate_node(graph, v):
    make_clique(graph, graph[v])
    delete_node(graph, v)

def delete_node(graph, v):
    for u in graph[v]:
        graph[u].remove(v)
    del graph[v]

def contract_edge(graph, u, v):
    """Contract edge (u,v) by removing u"""
    graph[v] = (graph[v] | graph[u]) - {u, v}
    del graph[u]
    for w in graph:
        if u in graph[w]:
            graph[w] = (graph[w] | {v}) - {u, w}

def copy_graph(graph):
    return {u:set(graph[u]) for u in graph}

def upper_bound(graph):
    """Min-fill."""
    graph = copy_graph(graph)
    dmax = 0
    order = []
    while len(graph) > 0:
        #d, u = min((len(graph[u]), u) for u in graph) # min-width
        d, u = min((count_fillin(graph, graph[u]), u) for u in graph)
        dmax = max(dmax, len(graph[u]))
        eliminate_node(graph, u)
        order.append(u)
    return dmax, order

def lower_bound(graph):
    """Minor-min-width"""
    graph = copy_graph(graph)
    dmax = 0
    while len(graph) > 0:
        # pick node of minimum degree
        d, u = min((len(graph[u]), u) for u in graph)
        dmax = max(dmax, d)

        # Gogate and Dechter: minor-min-width
        nb = graph[u] - {u}        
        if len(nb) > 0:
            _, v = min((len(graph[v] & nb), v) for v in nb)
            contract_edge(graph, u, v)
        else:
            delete_node(graph, u)
    return dmax

class Solution(object):
    pass

def quickbb(graph):
    """Gogate and Dechter, A complete anytime algorithm for treewidth. UAI
       2004. http://arxiv.org/pdf/1207.4109.pdf"""

    """Given a permutation of the nodes (called an elimination ordering),
       for each node, remove the node and make its neighbors into a clique.
       The maximum degree of the nodes at the time of their elimination is
       the width of the tree decomposition corresponding to that ordering.
       The treewidth of the graph is the minimum over all possible
       permutations.
       """

    best = Solution() # this gets around the lack of nonlocal in Python 2
    best.count = 0

    def bb(graph, order, f, g):
        best.count += 1
        if len(graph) < 2:
            if f < best.ub:
                assert f == g
                best.ub = f
                best.order = list(order) + list(graph)
        else:
            vs = []
            for v in graph:
                # very important pruning rule
                if simplicial(graph, v) or almost_simplicial(graph, v) and len(graph[v]) <= lb:
                    vs = [v]
                    break
                else:
                    vs.append(v)

            for v in vs:
                graph1 = copy_graph(graph)
                eliminate_node(graph1, v)
                order1 = order + [v]
                # treewidth for current order so far
                g1 = max(g, len(graph[v])) 
                # lower bound given where we are
                f1 = max(g, lower_bound(graph1)) 
                if f1 < best.ub:
                    bb(graph1, order1, f1, g1)

    graph = { u : set(graph[u]) for u in graph }

    order = []
    best.ub, best.order = upper_bound(graph)
    lb = lower_bound(graph)
    if lb < best.ub:
        bb(graph, order, lb, 0)

    # Build the tree decomposition
    tree = collections.defaultdict(set)
    def build(order):
        if len(order) < 2:
            bag = frozenset(order)
            tree[bag] = set()
            return
        v = order[0]
        clique = graph[v]
        eliminate_node(graph, v)
        build(order[1:])
        for tv in tree:
            if clique.issubset(tv):
                break
        bag = frozenset(clique | {v})
        tree[bag].add(tv)
        tree[tv].add(bag)
    build(best.order)
    return tree

if True and __name__ == "__main__":
    import fileinput, sys
    import graph

    s = []
    for line in fileinput.input():
        if line.lstrip().startswith('#'):
            continue
        s.append(line)
    s = ''.join(s)

    i = 0
    while i < len(s):
        try:
            g, i1 = graph.scan_graph(s, start=i, return_end=True)
        except:
            sys.stderr.write("couldn't read: %s\n" % s[i:i1])

        if g is None: break
        i = i1

        g = g.undirected_graph()

        tree = quickbb(g)
        print(max(len(tv)-1 for tv in tree))
        #print tree

if False and __name__ == "__main__":
    import fileinput, sys

    g = collections.defaultdict(set)
    for line in fileinput.input():
        if line.rstrip() == "END":
            break
        u, v = line.split()
        g[u].add(v)
        g[v].add(u)

    tree = quickbb(g)
    root = list(tree)[0]
    def visit(tu, indent, memo):
        if tu in memo: return
        memo.add(tu)
        print(" "*indent, " ".join(tu))
        for tv in tree[tu]:
            visit(tv, indent+2, memo)
    visit(root, 0, set())
    print("bags:", len(tree))
    print("width:", max(len(tv)-1 for tv in tree))
