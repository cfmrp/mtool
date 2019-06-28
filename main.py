#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
import sys;
import time;
from pathlib import Path;

import codec.amr;
import codec.conllu;
import codec.eds;
import codec.mrp;
import codec.sdp;
import codec.ucca;
import score.edm;
import score.mces;
import score.sdp;
import score.smatch;
import score.ucca;
import validate.core;
from analyzer import analyze;

__author__ = "oe"

VALIDATIONS = {"input", "anchors", "edges",
               "amr", "eds", "sdp", "ucca"}

def read_graphs(stream, format = None,
                full = False, normalize = False, reify = False,
                prefix = None, text = None, quiet = False,
                alignment = None, id = None, n = None, i = None):

  generator = None;
  if format == "amr":
    generator \
      = codec.amr.read(stream, full = full, reify = reify,
                       text = text,
                       alignment = alignment, quiet = quiet);
  elif format in {"ccd", "dm", "pas", "psd"}:
    generator = codec.sdp.read(stream, framework = format, text = text);
  elif format == "eds":
    generator = codec.eds.read(stream, reify = reify, text = text);
  elif format == "mrp":
    generator = codec.mrp.read(stream)
  elif format == "ucca":
    generator = codec.ucca.read(stream, text = text, prefix = prefix);
  elif format == "conllu" or format == "ud":
    generator = codec.conllu.read(stream, framework = format, text = text)
  else:
    print("read_graphs(): invalid input codec {}; exit."
          "".format(format), file = sys.stderr);
    sys.exit(1);

  if generator is None:
    return None, None;

  #
  # (for now) break out of the generators, for downstream simplicity
  #
  graphs = [];
  overlays = [];
  j = 0;
  while n is None or n < 1 or j < n:
    try:
      graph, overlay = next(generator);
      if id is not None:
        if graph.id == id:
          graphs.append(graph); overlays.append(overlay);
      elif i is not None and i >= 0:
        if j == i:
          graphs.append(graph); overlays.append(overlay);
          break;
      else:
        graphs.append(graph); overlays.append(overlay);
      j += 1;
    except StopIteration:
      break;

  if normalize:
    for graph in graphs: graph.normalize(normalize);

  return graphs, overlays;

def main():
  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--analyze", action = "store_true");
  parser.add_argument("--normalize", action = "append", default = []);
  parser.add_argument("--full", action = "store_true");
  parser.add_argument("--reify", action = "store_true");
  parser.add_argument("--ids", action = "store_true");
  parser.add_argument("--strings", action = "store_true");
  parser.add_argument("--gold", type = argparse.FileType("r"));
  parser.add_argument("--alignment", type = argparse.FileType("r"));
  parser.add_argument("--overlay", type = argparse.FileType("w"));
  parser.add_argument("--format");
  parser.add_argument("--score");
  parser.add_argument("--validate", action = "append", default = []);
  parser.add_argument("--limit", type = int, default = 0);
  parser.add_argument("--read", required = True);
  parser.add_argument("--write");
  parser.add_argument("--text");
  parser.add_argument("--prefix");
  parser.add_argument("--source");
  parser.add_argument("--i", type = int);
  parser.add_argument("--n", type = int);
  parser.add_argument("--id");
  parser.add_argument("--quiet", action = "store_true");
  parser.add_argument("--trace", "-t", action = "count", default = 0);
  parser.add_argument("input", nargs = "?",
                      type = argparse.FileType("r"), default = sys.stdin);
  parser.add_argument("output", nargs = "?",
                      type = argparse.FileType("w"), default = sys.stdout);
  arguments = parser.parse_args();

  text = None;
  if arguments.text:
    path = Path(arguments.text);
    if path.is_file():
      text = {};
      with path.open() as stream:
        for line in stream:
          id, string = line.split("\t", maxsplit = 1);
          if string.endswith("\n"): string = string[:len(string) - 1];
          text[id] = string;
    elif path.is_dir():
      text = path;

  if arguments.read not in {"mrp",
                            "ccd", "dm", "pas", "psd",
                            "eds", "ucca",
                            "amr",
                            "conllu", "ud"}:
    print("main.py(): invalid input format: {}; exit."
          "".format(arguments.read), file = sys.stderr);
    sys.exit(1);

  if arguments.write is not None and \
     arguments.write not in {"dot", "evaluation", "id", "json", "mrp", "txt"}:
    print("main.py(): invalid output format: {}; exit."
          "".format(arguments.write), file = sys.stderr);
    sys.exit(1);

  #
  # backwards compatibility: desirable until august 2019, say
  #
  if arguments.score == "mces": arguments.score = "mrp";
  if arguments.score is not None and \
     arguments.score not in {"mrp", "sdp", "edm", "ucca", "smatch"}:
    print("main.py(): invalid evaluation metric: {}; exit."
          "".format(arguments.score), file = sys.stderr);
    sys.exit(1);

  if arguments.format and \
     arguments.format not in {"mrp",
                              "ccd", "dm", "pas", "psd",
                              "eds", "ucca",
                              "amr",
                              "conllu", "ud"}:
    print("main.py(): invalid gold format: {}; exit."
          "".format(arguments.read), file = sys.stderr);
    sys.exit(1);

  normalizations = {"anchors", "case", "edges"};
  if len(arguments.normalize) == 1 and arguments.normalize[0] == "all":
    normalize = normalizations;
  else:
    normalize = set();
    for action in arguments.normalize:
      if action in normalizations:
        normalize.add(action);
      else:
        print("main.py(): invalid type of normalization: {}; exit."
              "".format(action), file = sys.stderr);
        sys.exit(1);
  if arguments.score is not None and len(normalize) == 0:
    normalize = normalizations;

  if arguments.alignment is not None and arguments.overlay is None:
    print("main.py(): option ‘--alignment’ requires ‘--overlay’; exit.",
          file = sys.stderr);
    sys.exit(1);
    
  graphs, overlays \
    = read_graphs(arguments.input, format = arguments.read,
                  full = arguments.full, normalize = normalize,
                  reify = arguments.reify, text = text,
                  alignment = arguments.alignment, quiet = arguments.quiet,
                  id = arguments.id, n = arguments.n, i = arguments.i);
  if not graphs:
    print("main.py(): unable to read input graphs; exit.", file = sys.stderr);
    sys.exit(1);

  if arguments.source:
    for graph in graphs: graph.source(arguments.source);

  if arguments.validate == ["all"]:
    actions = VALIDATIONS;
  else:
    actions = set();
    for action in arguments.validate:
      if action in VALIDATIONS:
        actions.add(action);
      else:
        print("main.py(): invalid type of validation: {}; exit."
              "".format(action), file = sys.stderr);
        sys.exit(1);

  if actions:
    for graph in graphs:
      validate.core.test(graph, actions, stream = sys.stderr);

  if arguments.analyze:
    analyze(graphs);

  if arguments.gold and arguments.score:
    if arguments.format is None: arguments.format = arguments.read;
    gold, _ = read_graphs(arguments.gold, format = arguments.format,
                          full = arguments.full, normalize = normalize,
                          reify = arguments.reify, text = text,
                          quiet = arguments.quiet,
                          id = arguments.id, n = arguments.n, i = arguments.i);
    if not gold:
      print("main.py(): unable to read gold graphs: {}; exit.", file = sys.stderr);
      sys.exit(1);
    for metric in arguments.score.split(","):
      result = None;
      launch = time.process_time();
      if metric == "edm":
        result = score.edm.evaluate(gold, graphs,
                                    format = arguments.write,
                                    trace = arguments.trace);
      elif metric == "mrp":
        result = score.mces.evaluate(gold, graphs,
                                     format = arguments.write,
                                     limit = arguments.limit,
                                     trace = arguments.trace);
      elif metric == "sdp":
        result = score.sdp.evaluate(gold, graphs,
                                    format = arguments.write,
                                    trace = arguments.trace);
      elif metric == "smatch":
        result = score.smatch.evaluate(gold, graphs,
                                       format = arguments.write,
                                       limit = arguments.limit,
                                       values = {"tops", "labels",
                                                 "properties", "anchors",
                                                 "edges", "attributes"},
                                       trace = arguments.trace);
      elif metric == "ucca":
        result = score.ucca.evaluate(gold, graphs,
                                     format = arguments.write,
                                     trace = arguments.trace);

      if result is not None:
        result["time"] = time.process_time() - launch;
        if arguments.write == "json" or True:
          #
          # _fix_me_
          # we should write a genuine custom JSON encoder
          #
          print("{", file = arguments.output, end = "");
          start = True;
          for key in result:
            if start: start = False;
            else: print(",\n ", file = arguments.output, end = ""     );
            print("\"{}\": ".format(key), file = arguments.output, end = "");
            json.dump(result[key], arguments.output, indent = None);
          print("}", file = arguments.output);
    sys.exit(0);
      
  for graph in graphs:
    if arguments.write in {"mrp", "evaluation"}:
      if arguments.write == "evaluation":
        graph.flavor = graph.framework = graph.nodes = graph.edges = None;
        if graph.source() in {"lpps"}:
          graph.targets(["dm", "psd", "eds", "ucca", "amr"]);
        elif graph.source() in {"brown", "wsj"}:
          graph.targets(["dm", "psd", "eds"]);
        elif graph.source() in {"ewt", "wiki"}:
          graph.targets(["ucca"]);
        elif graph.source() in {"amr-consensus", "bolt", "dfa",
                                "lorelei", "proxy", "xinhua"}:
          graph.targets(["amr"]);
      json.dump(graph.encode(), arguments.output,
                indent = None, ensure_ascii = False);
      print(file = arguments.output);
    elif arguments.write == "dot":
      graph.dot(arguments.output,
                ids = arguments.ids, strings = arguments.strings);
      print(file = arguments.output);
    elif arguments.write == "txt":
      print("{}\t{}".format(graph.id, graph.input), file = arguments.output);
    elif arguments.write == "id":
      print("{}".format(graph.id), file = arguments.output);

  if arguments.overlay:
    for graph in overlays:
      if graph:
        json.dump(graph.encode(), arguments.overlay,
                  indent = None, ensure_ascii = False);
        print(file = arguments.overlay);
    
if __name__ == "__main__":
  main();
