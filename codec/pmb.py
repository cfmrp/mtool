from operator import itemgetter;
import os.path;
import re;
import sys;
import xml.etree.ElementTree as ET;

from graph import Graph;

conditions = {"APX": "≈", "EQU": "=", "LEQ": "≤", "LES": "<", "NEQ": "≠",
              "SXN": "«", "SXP": "»", "SXY": "≖", "SZN": "\\", "SZP": "/",
              "STI": "⊍", "STO": "⊍", "SY1": "∥", "SY2": "⚮",
              "TAB": "⋈", "TPR": "≺"};

#
# in parsing the clauses, patterns are ordered by specificity
#
id_matcher = re.compile(r'^%%% bin/boxer --input (?:[^/]+/)?p([0-9]+)/d([0-9]+)/');
referent_matcher = re.compile(r'^(b[0-9]+) REF ([enpstx][0-9]+) +%(?: .* \[([0-9]+)\.\.\.([0-9]+)\])?$');
condition_matcher = re.compile(r'^(b[0-9]+) (EQU|NEQ|APX|LE[SQ]|TPR|TAB|S[ZX][PN]|ST[IO]|SY[12]|SXY) ([enpstx][0-9]+|"[^"]+") ([enpstx][0-9]+|"[^"]+") +%(?: .* \[([0-9]+)\.\.\.([0-9]+)\])?$');
role_matcher = re.compile(r'^(b[0-9]+) ([^ ]+) ([enpstx][0-9]+) ([enpstx][0-9]+|"[^"]+") +%(?: .* \[([0-9]+)\.\.\.([0-9]+)\])?$');
concept_matcher = re.compile(r'^(b[0-9]+) ([^ ]+) ("[^ ]+") ([enpstx][0-9]+) +%(?: .* \[([0-9]+)\.\.\.([0-9]+)\])?$');
discourse_matcher = re.compile(r'^(b[0-9]+) ([^ ]+) (b[0-9]+)(?: (b[0-9]+))? +%(?: .* \[[0-9]+\.\.\.[0-9]+\])?$');
empty_matcher = re.compile(r'^ *%(?: .* \[[0-9]+\.\.\.[0-9]+\])?$');

def read(fp, text = None, full = False, reify = False, trace = 0, strict = 0):

  def finish(graph, mapping, finis, scopes):
    if reify:
      for box, referent, node in finis:
        #
        # in full reification mode, or when the corresponding box cannot be
        # easily inferred for a reified role (including when the source node is
        # a constant, as e.g. in a 'future' temporal discourse conditions),
        # add an explicit box membership edge.
        #
        if full \
           or referent[0] == referent[-1] == "\"" \
           or box not in scopes[referent]:
          graph.add_edge(mapping[box].id, node.id, "∈");
    else:
      for referent in scopes:
        if len(scopes[referent]) > 1:
          print("pbm.read(): [graph #{}] stray referent ‘{}’ in boxes {}."
                "".format(graph.id, referent, scopes[referent]),
                file=sys.stderr);
    #
    # after the fact, mark all boxes that structurally are roots as top nodes.
    #
    for node in graph.nodes:
      if node.type == 0 and node.is_root(): node.is_top = True;
 
  graph = None; id = None; sentence = None;
  mapping = dict(); scopes = dict(); finis = list();
  i = 0;
  header = 3;
  for line in fp:
    line = line.rstrip(); i += 1;
    if trace: print("{}: {}".format(i, line));
    #
    # to support newline-separated concatenations of clause files (a format not
    # used in the native PMB 3.0 release), 
    #
    if len(line) == 0:
      finish(graph, mapping, finis, scopes);
      yield graph, None;
      graph = None; id = None;
      mapping = dict(); scopes = dict(); finis = list();
      header = 3;
      continue;
    #
    # each block of clauses is preceded by three comment lines, which we use to
    # extract the sentence identifier and underlying string.
    #
    if header:
      if header == 3: pass;
      elif header == 2:
        match = id_matcher.match(line);
        if match is None:
          raise Exception("pbm.read(): "
                          "[line {}] missing identifier in ‘{}’; exit."
                          "".format(i, line));
        part, document = match.groups();
        id = "{:02d}{:04d}".format(int(part), int(document));
      elif header == 1:
        if text is not None and id in text: sentence = text[id];
        else: sentence = line[5:-1];
        graph = Graph(id, flavor = 2, framework = "drg");
        graph.add_input(sentence);
      header -= 1;
      continue;
    #
    # from here onwards, we are looking at genuine, contentful clauses.  from
    # inspecting some of the files, it appears they are organized according to
    # surface (reading) order, and we cannot assume that discourse referents
    # are 'introduced' (in some box) prior to their first occurance in e.g. a
    # role or concept clause.
    #
    anchor = None;
    match = referent_matcher.match(line);
    if match is not None:
      box, referent, start, end = match.groups();
      if referent in scopes:
        if strict and box not in scopes[referent] and reify:
          raise Exception("pbm.read(): "
                          "[line {}] stray referent ‘{}’ in box ‘{}’ "
                          "(instead of ‘{}’); exit."
                          "".format(i, referent, box, scopes[referent]));
      else: scopes[referent] = {box};
      if box not in mapping: mapping[box] = graph.add_node(type = 0);
      if start is not None and end is not None:
        anchor = {"from": int(start), "to": int(end)};
      if referent not in mapping:
        mapping[referent] \
          = graph.add_node(anchors = [anchor] if anchor else None);
      else:
        node = mapping[referent];
        node.add_anchor(anchor);
      graph.add_edge(mapping[box].id, mapping[referent].id, "∈");
    else:
      match = condition_matcher.match(line);
      if match is not None:
        box, condition, source, target, start, end = match.groups();
        condition = conditions[condition];
        if source[0] == "\"" and source[-1] == "\"" and source not in mapping:
          if start is not None and end is not None:
            anchor = {"from": int(start), "to": int(end)};
          mapping[source] \
            = graph.add_node(label = source,
                             anchors = [anchor] if anchor else None);
        elif source not in mapping: mapping[source] = graph.add_node();
        if target[0] == "\"" and target[-1] == "\"" and target not in mapping:
          if start is not None and end is not None:
            anchor = {"from": int(start), "to": int(end)};
          mapping[target] \
            = graph.add_node(label = target,
                             anchors = [anchor] if anchor else None);
        elif target not in mapping: mapping[target] = graph.add_node();
        if reify:
          if box not in mapping: mapping[box] = graph.add_node(type = 0);
          node = graph.add_node(label = condition, type = 3);
          finis.append((box, source, node));
          graph.add_edge(mapping[source].id, node.id, None);
          graph.add_edge(node.id, mapping[target].id, None);
        else:
          if source in scopes: scopes[source].add(box);
          else: scopes[source] = {box};
          graph.add_edge(mapping[source].id, mapping[target].id, condition);
      else:
        match = role_matcher.match(line);
        if match is not None:
          box, role, source, target, start, end = match.groups();
          if source not in mapping: mapping[source] = graph.add_node();
          if target[0] == "\"" and target[-1] == "\"" and target not in mapping:
            if start is not None and end is not None:
              anchor = {"from": int(start), "to": int(end)};
            mapping[target] \
              = graph.add_node(label = target,
                               anchors = [anchor] if anchor else None);
          elif target not in mapping: mapping[target] = graph.add_node();
          if reify:
            if box not in mapping: mapping[box] = graph.add_node(type = 0);
            node = graph.add_node(label = role, type = 2);
            finis.append((box, source, node));
            graph.add_edge(mapping[source].id, node.id, None);
            graph.add_edge(node.id, mapping[target].id, None);
          else:
            if source in scopes: scopes[source].add(box);
            else: scopes[source] = {box};
            graph.add_edge(mapping[source].id, mapping[target].id, role);
        else:
          match = concept_matcher.match(line);
          if match is not None:
            box, lemma, sense, referent, start, end = match.groups();
            if referent in scopes:
              if strict and box not in scopes[referent] and reify:
                raise Exception("pbm.read(): "
                                "[line {}] stray referent ‘{}’ in box ‘{}’ "
                                "(instead of ‘{}’); exit."
                                "".format(i, referent, box, scopes[referent]));
            else: scopes[referent] = {box};
            if start is not None and end is not None:
              anchor = {"from": int(start), "to": int(end)};
            if referent not in mapping:
              mapping[referent] = node \
                = graph.add_node(anchors = [anchor] if anchor else None);
            else:
              node = mapping[referent];
              node.add_anchor(anchor);
            if strict and node.label is not None:
              raise Exception("pbm.read(): "
                              "[line {}] duplicate label ‘{}’ on referent ‘{}’ "
                              "(instead of ‘{}’); exit."
                              "".format(i, lemma, referent, node.label));
            node.label = lemma;
            if sense[0] == sense[-1] == "\"": sense = sense[1:-1];
            node.set_property("sense", sense);
          else:
            match = discourse_matcher.match(line);
            if match is not None:
              top, relation, one, two = match.groups();
              if one not in mapping: mapping[one] = graph.add_node(type = 0);
              if two is not None:
                if trace > 1: print("ternary discourse relation");
                if two not in mapping: mapping[two] = graph.add_node(type = 0);
                graph.add_edge(mapping[one].id, mapping[two].id, relation);
              else:
                if top not in mapping: mapping[top] = graph.add_node(type = 0);
                graph.add_edge(mapping[top].id, mapping[one].id, relation);
            elif empty_matcher.search(line) is None:
              raise Exception("pmb.read(): [line {}] invalid clause ‘{}’."
                              "".format(i, line));
  #
  # finally, as we reach an end of file (without an empty line terminating the
  # preceding block of clauses, as is the standard format in PMB), finalize the
  # graph and return it.
  #
  if graph is not None:
    finish(graph, mapping, finis, scopes);
    yield graph, None;
    
