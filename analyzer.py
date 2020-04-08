# GraphaLogue Analyzer
# Marco Kuhlmann <marco.kuhlmann@liu.se>

import itertools
import statistics
import sys

from graph import Graph
from treewidth import quickbb


class DepthFirstSearch(object):

    def __init__(self, graph, undirected=False):
        self._graph = graph
        self._undirected = undirected

        self._enter = dict()
        self._leave = dict()
        self.n_runs = 0

        def compute_timestamps(node, timestamp):
            self._enter[node] = next(timestamp)
            for edge in self._graph.find_node(node).outgoing_edges:
                if not edge.tgt in self._enter:
                    compute_timestamps(edge.tgt, timestamp)
            if self._undirected:
                for edge in self._graph.find_node(node).incoming_edges:
                    if not edge.src in self._enter:
                        compute_timestamps(edge.src, timestamp)
            self._leave[node] = next(timestamp)
        timestamp = itertools.count()
        for node in self._graph.nodes:
            if not node.id in self._enter:
                compute_timestamps(node.id, timestamp)
                self.n_runs += 1

    def is_back_edge(self, edge):
        return \
            self._enter[edge.tgt] < self._enter[edge.src] and \
            self._leave[edge.src] < self._leave[edge.tgt]


class InspectedGraph(object):

    def __init__(self, graph):
        self.graph = graph
        self.n_nodes = len(graph.nodes)
        self.dfs = DepthFirstSearch(graph)
        self.undirected_dfs = DepthFirstSearch(graph, undirected=True)

    def n_root_nodes(self):
        return sum(1 for node in self.graph.nodes if node.is_root())

    def n_leaf_nodes(self):
        return sum(1 for node in self.graph.nodes if node.is_leaf())

    def n_top_nodes(self):
        return sum(1 for node in self.graph.nodes if node.is_top())

    def n_singleton_nodes(self):
        return sum(1 for node in self.graph.nodes if node.is_singleton())

    def n_loops(self):
        return sum(1 for edge in self.graph.edges if edge.is_loop())

    def n_components(self):
        return self.undirected_dfs.n_runs - self.n_singleton_nodes()

    def is_cyclic(self):
        for edge in self.graph.edges:
            if edge.is_loop() or self.dfs.is_back_edge(edge):
                return True
        return False

    def is_forest(self):
        if self.is_cyclic():
            return False
        else:
            for node in self.graph.nodes:
                if len(node.incoming_edges) > 1:
                    return False
            return True

    def is_tree(self):
        return self.is_forest() and self.n_components() == 1

    def treewidth(self):
        n_nodes = len(self.graph.nodes) - self.n_singleton_nodes()
        if n_nodes <= 1:
            return 1
        else:
            undirected_graph = {}
            for node in self.graph.nodes:
                if not node.is_singleton():
                    undirected_graph[node.id] = set()
            for edge in self.graph.edges:
                if not edge.is_loop():
                    undirected_graph[edge.src].add(edge.tgt)
                    undirected_graph[edge.tgt].add(edge.src)
            decomposition = quickbb(undirected_graph)
            return max(1, max(len(u)-1 for u in decomposition))

    def _crossing_pairs(self):
        def endpoints(edge):
            return (min(edge.src, edge.tgt), max(edge.src, edge.tgt))
        for edge1 in self.graph.edges:
            min1, max1 = endpoints(edge1)
            for edge2 in self.graph.edges:
                min2, max2 = endpoints(edge2)
                if min1 < min2 and min2 < max1 and max1 < max2:
                    yield (min1, max1), (min2, max2)

    def _crossing_edges(self):
        crossing_edges = set()
        for edge1, edge2 in self._crossing_pairs():
            crossing_edges.add(edge1)
            crossing_edges.add(edge2)
        return crossing_edges

    def is_noncrossing(self):
        for _, _ in self._crossing_pairs():
            return False
        return True

    def is_page2(self):
        crossing_graph = {u: set() for u in self._crossing_edges()}
        for edge1, edge2 in self._crossing_pairs():
            crossing_graph[edge1].add(edge2)
            crossing_graph[edge2].add(edge1)

        # Tests whether the specified undirected graph is 2-colorable.
        colors = {}

        def inner(node, color1, color2):
            colors[node] = color1
            for neighbour in crossing_graph[node]:
                if neighbour in colors:
                    if colors[neighbour] == color1:
                        return False
                else:
                    inner(neighbour, color2, color1)
            return True

        for node in crossing_graph:
            if node not in colors:
                if not inner(node, 0, 1):
                    return False
        return True

    def density(self):
        n_nodes = len(self.graph.nodes) - self.n_singleton_nodes()
        if n_nodes <= 1:
            return 1
        else:
            n_edges = 0
            for edge in self.graph.edges:
                if edge.src != edge.tgt:
                    n_edges += 1
            return n_edges / (n_nodes - 1)


PROPERTY_COUNTER = itertools.count(1)


def report(msg, val):
    print("(%02d)\t%s\t%s" % (next(PROPERTY_COUNTER), msg, val))


def analyze(graphs, ids=None):
    ordered = False
    n_graphs = 0
    n_graphs_noncrossing = 0
    n_graphs_has_top_node = 0
    n_graphs_multirooted = 0
    n_nodes = 0
    n_nodes_with_reentrancies = 0
    n_singletons = 0
    n_top_nodes = 0
    n_edges = 0
    n_labels = 0;
    n_properties = 0;
    n_anchors = 0;
    n_attributes = 0;
    n_loops = 0
    labels = set()
    non_functional_labels = set()
    n_cyclic = 0
    n_connected = 0
    n_forests = 0
    n_trees = 0
    n_graphs_page2 = 0
    acc_treewidth = 0
    n_roots_nontop = 0
    acc_density = 0.0
    max_treewidth = 0
    acc_edge_length = 0
    n_treewidth_one = 0
    treewidths = []
    for graph in graphs:
        if ids and not graph.id in ids:
            continue

        n_graphs += 1
        n_nodes += len(graph.nodes)
        n_edges += len(graph.edges)

        for node in graph.nodes:
            if node.label is not None: n_labels += 1;
            if node.properties is not None and node.values is not None:
                n_properties += len(node.properties);
            if node.anchors is not None: n_anchors += 1;
        for edge in graph.edges:
            if edge.attributes is not None and edge.values is not None:
                n_attributes += len(edge.attributes);

        inspected_graph = InspectedGraph(graph)

        treewidth = inspected_graph.treewidth()

        n_trees += inspected_graph.is_tree()
        acc_density += inspected_graph.density()

        has_reentrancies = False
        has_top_node = False

        n_loops += inspected_graph.n_loops()

        for edge in graph.edges:
            labels.add(edge.lab)
        for node in graph.nodes:
            n_top_nodes += node.is_top
            if node.is_top:
                has_top_node = True
            n_singletons += node.is_singleton()
            if len(node.incoming_edges) > 1:
                n_nodes_with_reentrancies += 1
                has_reentrancies = True
            outgoing_labels = set()
            for edge in node.outgoing_edges:
                if edge.lab in outgoing_labels:
                    non_functional_labels.add(edge.lab)
                else:
                    outgoing_labels.add(edge.lab)
            if not node.is_singleton() and node.is_root() and not node.is_top:
                n_roots_nontop += 1

        n_cyclic += inspected_graph.is_cyclic()
        n_connected += inspected_graph.n_components() == 1
        n_forests += inspected_graph.is_forest()
        acc_treewidth += treewidth
        max_treewidth = max(max_treewidth, treewidth)
        n_treewidth_one += treewidth == 1
        treewidths.append(treewidth)

        if graph.flavor == 0:
            ordered = True
            n_graphs_noncrossing += inspected_graph.is_noncrossing()
            n_graphs_page2 += inspected_graph.is_page2()
            acc_edge_length += sum(edge.length() for edge in graph.edges)
        else:
            if ordered:
                print(
                    "analyzer.py: cannot mix graphs of different flavors in one file; exit.", file=sys.stderr)
                sys.exit(1)

        n_graphs_has_top_node += has_top_node
        n_graphs_multirooted += inspected_graph.n_root_nodes() > 1

    n_nonsingletons = n_nodes - n_singletons

    report("number of graphs", "%d" % n_graphs)
    report("number of nodes", "%d" % n_nodes)
    n_tuples = n_top_nodes + n_labels + n_properties + n_anchors + n_edges + n_attributes;
    if n_tuples > 0:
      report("number of tops (percentage)",
             "{:d} ({:.2f})".format(n_top_nodes, 100 * n_top_nodes / n_tuples));
      report("number of node labels (percentage)",
             "{:d} ({:.2f})".format(n_labels, 100 * n_labels / n_tuples));
      report("number of node properties (percentage)",
             "{:d} ({:.2f})".format(n_properties, 100 * n_properties / n_tuples));
      report("number of node anchors (percentage)",
             "{:d} ({:.2f})".format(n_anchors, 100 * n_anchors / n_tuples));
      report("number of edges (percentage)",
             "{:d} ({:.2f})".format(n_edges, 100 * n_edges / n_tuples));
      report("number of edge attributes (percentage)",
             "{:d} ({:.2f})".format(n_attributes, 100 * n_attributes / n_tuples));
    report("number of edge labels", "%d" % len(labels))
#    report("\\percentnode\\ singleton", "%.2f" % (100 * n_singletons / n_nodes))
#    report("\\percentnode\\ non-singleton", "%.2f" % (100 * n_nonsingletons / n_nodes))
    report("\\percentgraph\\ trees", "%.2f" % (100 * n_trees / n_graphs))
    report("\\percentgraph\\ treewidth one", "%.2f" %
           (100 * n_treewidth_one / n_graphs))
    report("average treewidth", "%.3f" % (acc_treewidth / n_graphs))
#    report("median treewidth", "%d" % statistics.median(treewidths))
    report("maximal treewidth", "%d" % max_treewidth)
#    report("edge density", "%.3f" % (n_edges / n_nonsingletons))
    report("average edge density", "%.3f" % (acc_density / n_graphs))
    report("\\percentnode\\ reentrant", "%.2f" %
           (100 * n_nodes_with_reentrancies / n_nonsingletons))
#    report("labels", " ".join(sorted(labels)))
#    report("functional labels", " ".join(sorted(labels - non_functional_labels)))
#    report("non-functional labels", " ".join(sorted(non_functional_labels)))
#    report("\\percentgraph\\ forests", "%.2f" % (100 * n_forests / n_graphs))
#    report("number of top nodes", "%d" % n_top_nodes)
    report("\\percentgraph\\ cyclic", "%.2f" % (100 * n_cyclic / n_graphs))
#    report("number of self-loops", "%d" % n_loops)
    report("\\percentgraph\\ not connected", "%.2f" %
           (100 * (n_graphs - n_connected) / n_graphs))
#    report("\\percentgraph\\ without top", "%.2f" % (100 * (n_graphs - n_graphs_has_top_node) / n_graphs))
#    report("average top nodes per graph", "%.3f" % (n_top_nodes / n_graphs))
    report("\\percentgraph\\ multi-rooted", "%.2f" %
           (100 * n_graphs_multirooted / n_graphs))
    report("percentage of non-top roots", "%.2f" %
           (100 * n_roots_nontop / n_nonsingletons))
    if ordered:
        report("average edge length", "%.3f" % (acc_edge_length / n_edges))
        report("\\percentgraph\\ noncrossing", "%.2f" %
               (100 * n_graphs_noncrossing / n_graphs))
        report("\\percentgraph\\ pagenumber two", "%.2f" %
               (100 * n_graphs_page2 / n_graphs))
    else:
        report("average edge length", "--")
        report("\\percentgraph\\ noncrossing", "--")
        report("\\percentgraph\\ pagenumber two", "--")


def read_ids(file_name):
    ids = set()
    with open(file_name) as fp:
        for line in fp:
            ids.add(line.rstrip())
    return ids


def read_tokens(file_name):
    with open(file_name) as fp:
        for line in fp:
            yield line.split()


def analyze_cmd(read_function, ordered=False):
    import sys
    ids = None
    tokens = None
    for arg in sys.argv[2:]:
        x, y = tuple(arg.split(':'))
        if x == 'ids':
            print("Reading whitelisted IDs from %s" % y, file=sys.stderr)
            ids = read_ids(y)
        if x == 'tokens':
            print("Reading tokens from %s" % y, file=sys.stderr)
            tokens = read_tokens(y)
    with open(sys.argv[1]) as fp:
        analyze(read_function(fp), ordered=ordered, ids=ids, tokens=tokens)
