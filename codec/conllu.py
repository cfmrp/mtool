import re;
import sys;

from graph import Graph;

TEXT = re.compile(r"^# text = (.+)$");
ID = re.compile(r"^# sent_id = (.+)$");
RANGE = re.compile(r"^([0-9]+)-([0-9]+)$");
ANCHOR = re.compile(r".*TokenRange=([0-9]+):([0-9]+)");

def read_tuples(stream):
  id, input = None, None;
  tuples = [];
  for line in stream:
    line = line.rstrip();
    if line.startswith("#"):
      match = TEXT.match(line)
      if match:
        input = match.group(1);
        continue;
      match = ID.match(line);
      if match:
        id = match.group(1);
        continue;
    elif len(line) == 0:
      # if there is no `text` comment in the conll, one should reconstruct
      # the input sentence from the FORM column, since it is required in :construct_graph
      if input is None:
        input = reconstruct_input_from_tuples(tuples)
      if tuples:
        yield id, input, tuples;
        id, input = None, None;
        tuples = []
    else:
      tuples.append(line.split("\t"));

def reconstruct_input_from_tuples(tuples):
  """ Reconstruct input sentence from the CoNLL-U representation.
  each tuple in tuples correspond to a line in a block. """
  if not tuples: return ''
  # iterate only surface tokens - discard empty nodes and tokens included in ranges
  surface_indicator = get_is_surface_token_indicator(tuples)
  surface_tuples = [tuple
                    for is_surface, tuple in zip(surface_indicator, tuples)
                    if is_surface]
  sent_str = ''
  for t in surface_tuples:
    tok = t[1] # FORM column
    sent_str += tok
    if "SpaceAfter=No" not in t[-1] and t is not tuples[-1]: # Misc. column (last column)
      # in last token, don't add space in any case
      sent_str += ' '

  return sent_str

def get_ids2range_tuple(tuples):
  """
  Return Dict[int: tuple].
   for each node-id k that is part of a multi-word token (denoted by range-id "i-j"), let t be the tuple
   of the token i-j (the multiword token). the dict will be {k:t} over all these ks.
  """
  ranges2multiword = dict()
  for tuple in tuples:
    match = RANGE.match(tuple[0])
    if match is not None:
      for t in range(int(match.group(1)), int(match.group(2)) + 1):
        ranges2multiword[t] = tuple
  return ranges2multiword

def get_is_surface_token_indicator(tuples):
  """
  Return a list of boolean in same length as `tuples`,
  where output[i] indicate whether tuple[i] correspond to a surface token.
  surface tokens are those tokens that are required for detokenization of input sentence.
  see https://universaldependencies.org/format.html#words-tokens-and-empty-nodes

  the conditions to be a surface token -
    1. be not an empty node (in the form "i.j")
    2. be not a (syntactic) word that is contained in a multi-word token. that is, the word's id
    isn't included in any range-id (in the form "i-j").
  """
  ids2range_tuple = get_ids2range_tuple(tuples)
  ids = [t[0] for t in tuples]
  surface_indicator = ["." not in tid # condition 1.
                       and ("-" in tid or int(tid) not in ids2range_tuple) # condition 2.
                       for tid in ids]
  return surface_indicator

def read_anchors(stream):
  if stream is None:
    while True: yield None, None;
  else:
    id = None;
    tokens = list();
    for line in stream:
      line = line.rstrip("\n");
      if len(line) == 0:
        yield id, tokens;
        id = None;
        tokens.clear();
      elif line.startswith("#"):
        id = line[1:];
      else:
        fields = line.split("\t");
        if len(fields) == 3:
          tokens.append((int(fields[0]), int(fields[1])));
    if len(tokens) > 0:
      yield id, tokens;

def construct_graph_nodes(id, input, tuples, framework, text, anchors):
  i = 0;
  def compute(form):
    nonlocal i;
    m = None;
    j = input.find(form, i);
    if j >= i:
      i, m = j, len(form);
    else:
      base = form;
      k, l = len(input), 0;
      for old, new in {("‘", "`"), ("‘", "'"), ("’", "'"), ("`", "'"),
                       ("“", "\""), ("”", "\""),
                       ("–", "--"), ("–", "---"), ("—", "---"),
                       ("…", "..."), ("…", ". . .")}:
        form = base.replace(old, new);
        j = input.find(form, i);
        if j >= i and j < k: k, l = j, len(form);
      if k < len(input): i, m = k, l;
    if m:
      match = {"from": i, "to": i + m};
      i += m;
      return match;
    else:
      raise Exception("[{}] failed to anchor |{}| in |{}|{}| ({})"
                      "".format(graph.id, form, input[:i], input[i:], i));

  graph = Graph(id, flavor = 0, framework = framework);
  if input is not None: graph.add_input(input);
  elif text is not None: graph.add_input(text);
  input = graph.input;

  anchors_generator = read_anchors(anchors);
  _, anchors_tokens = next(anchors_generator);
  id, ids = 0, dict();
  ids2range_tuple = get_ids2range_tuple(tuples)
  for tuple, is_surface_token in zip(tuples, get_is_surface_token_indicator(tuples)):
    id += 1;
    ids[tuple[0]] = id;
    form, lemma, upos, xpos, features, head, misc = \
      tuple[1], tuple[2], tuple[3], tuple[4], tuple[5], tuple[6], tuple[9];
    properties = {"lemma": lemma, "upos": upos, "xpos": xpos};
    if features != "_":
      for feature in features.split("|"):
        name, value = feature.split("=", 1);
        properties[name] = value;
    # retrieve anchoring - only for surface tokens
    if not is_surface_token:
      anchors = []
    elif anchors_tokens is not None:
      start, end = anchors_tokens.pop(0);
      anchors = [{"from": start, "to": end}];
    else:
      tid = tuple[0]
      if tid.isnumeric() and int(tid) in ids2range_tuple:
        range_tuple_misc = ids2range_tuple[int(tid)][9];
        if range_tuple_misc != "_":
          misc = range_tuple_misc
      match = ANCHOR.match(misc);
      if match:
        anchors = [{"from": int(match.group(1)), "to": int(match.group(2))}];
      else:
        anchors = [compute(form)];
    graph.add_node(id, label = form,
                   properties = list(properties.keys()),
                   values = list(properties.values()),
                   top = True if head == "0" else False,
                   anchors = anchors);
  return graph, ids;

def construct_graph_edges(tuples, graph, ids):
  """ Given a graph with nodes (and id-mapping) pre-constructed,
  read edges from tuples and add them to graph.
  Modifies `graph` argument. """
  for tuple in tuples:
    id, head, type = tuple[0], tuple[6], tuple[7]
    if head in ids:
      graph.add_edge(ids[head], ids[id], type)

def construct_enhanced_graph_edges(tuples, graph, ids):
  """ Given a graph with nodes (and id-mapping) pre-constructed,
  read edges from tuples and add them to graph.
  This function is for reading Enhance UD graphs, which is distinguished from reading
  basic UD only in source of edges information -- DEPS column instead of HEAD, DEPREL columns.
  See https://universaldependencies.org/format.html#syntactic-annotation for EUD format specifications
  which we follow here.
  Modifies `graph` argument. """
  for tuple in tuples:
    id, deps = tuple[0], tuple[8]
    if deps == "_": # empty list of relations
      continue
    for rel in deps.split("|"): # relations are delimited with bar
      head, dep_type = rel.split(":", 1)
      if head in ids:
        graph.add_edge(ids[head], ids[id], dep_type)


def construct_graph(id, input, tuples, framework = None, text = None, anchors = None, enhanced_graph=False):
  graph, ids = construct_graph_nodes(id, input, tuples, framework, text, anchors)
  if not enhanced_graph:
    # basic UD graph (default)
    construct_graph_edges(tuples, graph, ids)
  else:
    # Enhanced UD graphs
    construct_enhanced_graph_edges(tuples, graph, ids)
  return graph

def read(stream, framework = None, text = None, anchors = None, trace = 0, enhanced_graph=False):
  tuples_generator = read_tuples(stream)
  for id, input, tuples in tuples_generator:
    if trace:
      print("conllu.read(): processing graph #{} ...".format(id),
            file = sys.stderr);
    graph = construct_graph(id, input, tuples, framework, text, anchors, enhanced_graph)
    yield graph, None;
