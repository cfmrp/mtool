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
      return id, input, tuples;
    else:
      tuples.append(line.split("\t"));
  return id, input, None;

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

def construct_graph(id, input, tuples, framework = None, text = None, anchors = None):
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
      raise Exception("failed to anchor |{}| in |{}|{}| ({})"
                      "".format(form, input[:i], input[i:], i));

  graph = Graph(id, flavor = 0, framework = framework);
  if input is not None: graph.add_input(input);
  elif text is not None: graph.add_input(text);
  input = graph.input;

  generator = read_anchors(anchors);
  _, tokens = next(generator);
  id, ids = 0, dict();
  ranges = dict();
  for tuple in tuples:
    match = RANGE.match(tuple[0]);
    if match is not None and tuple[9] != "_":
      for t in range(int(match.group(1)), int(match.group(2)) + 1):
        ranges[t] = tuple[9];
    else:
      id += 1;
      ids[tuple[0]] = id;
      form, lemma, upos, xpos, features, root, misc = \
        tuple[1], tuple[2], tuple[3], tuple[4], tuple[5], int(tuple[6]), tuple[9];
      properties = {"lemma": lemma, "upos": upos, "xpos": xpos};
      if features != "_":
        for feature in features.split("|"):
          name, value = feature.split("=");
          properties[name] = value;
      if tokens is not None:
        start, end = tokens.pop(0);
        anchors = [{"from": start, "to": end}];
      else:
        if int(tuple[0]) in ranges: misc = ranges[int(tuple[0])];
        match = ANCHOR.match(misc);
        if match:
          anchors = [{"from": int(match.group(1)), "to": int(match.group(2))}];
        else:
          anchors = [compute(form)];
      graph.add_node(id, label = form,
                     properties = list(properties.keys()),
                     values = list(properties.values()),
                     top = True if root == 0 else False,
                     anchors = anchors);

  for tuple in tuples:
    id, head, type = tuple[0], tuple[6], tuple[7];
    if head in ids:
      graph.add_edge(ids[head], ids[id], type);

  return graph;

def read(stream, framework = None, text = None, anchors = None, trace = 0):
  id, input, tuples = read_tuples(stream);
  while tuples:
    if trace:
      print("conllu.read(): processing graph #{} ...".format(id),
            file = sys.stderr);
    yield construct_graph(id, input, tuples, framework, text, anchors), None;
    id, input, tuples = read_tuples(stream);
