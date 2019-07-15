import re;

from graph import Graph;

def read_tuples(stream):
  id = None;
  tuples = [];
  for line in stream:
    line = line.rstrip();
    if line.startswith("#"):
      match = re.match(r"^#(.+)$", line);
      if match:
        id = match.group(1);
    else:
      if len(line) == 0:
        return id, tuples;
      else:
        tuples.append(line.split("\t"));
  return id, None;

def read_anchors(stream):
  if stream is None:
    while True: yield None, None;
  else: 
    id = None;
    tokens = list();
    for line in stream:
      line = line.strip();
      if len(line) == 0:
        yield id, tokens;
        id = None;
        tokens.clear();
      else:
        if line.startswith("#"):
          id = line[1:];
        else:
          fields = line.split("\t");
          if len(fields) == 3:
            tokens.append((int(fields[0]), int(fields[1])));
    if len(tokens) > 0:
      yield id, tokens;

def construct_graph(id, tuples, framework = None, text = None, anchors = None):
  graph = Graph(id, flavor = 0, framework = framework);
  generator = read_anchors(anchors);
  _, tokens = next(generator);
  ids = {};
  for id, tuple in enumerate(tuples):
    ids[tuple[0]] = id;
    form, lemma, upos, xpos, root, misc = \
      tuple[1], tuple[2], tuple[3], tuple[4], int(tuple[6]), tuple[9];
    properties = {"lemma": lemma, "upos": upos, "xpos": xpos};
    if tokens is not None:
      start, end = tokens.pop(0);
      anchors = [{"from": start, "to": end}];
    else:
      match = re.match(r"TokenRange=([0-9]+):([0-9]+)", misc);
      if match:
        anchors = [{"from": int(match.group(1)), "to": int(match.group(2))}];
      else:
        anchors = None;
    graph.add_node(id, label = form,
                   properties = list(properties.keys()),
                   values = list(properties.values()),
                   top = True if root == 0 else False,
                   anchors = anchors);

  for tuple in tuples:
    id, head, type = tuple[0], tuple[6], tuple[7];
    if head in ids:
      graph.add_edge(ids[head], ids[id], type);

  if text:
    graph.add_input(text);

  return graph;

def read(stream, framework = None, text = None, anchors = None):
  id, tuples = read_tuples(stream);
  while tuples:
    yield construct_graph(id, tuples, framework, text, anchors), None;
    id, tuples = read_tuples(stream);
