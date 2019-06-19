#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
from pathlib import Path;
import sys;

from analyzer import analyze;
from graph import Graph;

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

from version import __version__;

__author__ = "oe"


def read_graphs(stream, format = None,
                full = False, normalize = False, reify = False,
                prefix = None, text = None,
                id = None, n = None, i = None):

  graphs = None;
  if format == "amr":
    graphs = codec.amr.read(stream, full = full,
                            reify = reify, text = text);
  elif format in {"ccd", "dm", "pas", "psd"}:
    graphs = codec.sdp.read(stream, framework = format, text = text);
  elif format == "eds":
    graphs = codec.eds.read(stream, reify = reify, text = text);
  elif format == "mrp":
    graphs = codec.mrp.read(stream)
  elif format == "ucca":
    graphs = codec.ucca.read(stream, text = text, prefix = prefix);
  elif format == "conllu" or format == "ud":
    graphs = codec.conllu.read(stream, framework = format, text = text)
  else:
    print("read_graphs(): invalid input codec {}; exit."
          "".format(format), file = sys.stderr);
    sys.exit(1);

  #
  # for now, break out of the generators, for downstream simplicity
  #
  graphs = list(graphs);
  
  if id is not None:
    graphs = [graph for graph in graphs if graph.id == id];
  elif i is not None and i >= 0:
    graphs = graphs[i:i + 1];
  elif n is not None and n >= 1:
    graphs = graphs[0:n]

  if normalize:
    for graph in graphs: graph.normalize(normalize);

  return graphs;

def main():
  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--analyze", action = "store_true");
  parser.add_argument("--normalize", action = "append", default = []);
  parser.add_argument("--full", action = "store_true");
  parser.add_argument("--reify", action = "store_true");
  parser.add_argument("--strings", action = "store_true");
  parser.add_argument("--gold", type = argparse.FileType("r"));
  parser.add_argument("--format");
  parser.add_argument("--score");
  parser.add_argument("--validate", action = "append", default = []);
  parser.add_argument("--limit", type = int, default = 0);
  parser.add_argument("--read", required = True);
  parser.add_argument("--write");
  parser.add_argument("--text");
  parser.add_argument("--prefix");
  parser.add_argument("--i", type = int);
  parser.add_argument("--n", type = int);
  parser.add_argument("--id");
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
     arguments.write not in {"dot", "id", "json", "mrp", "txt"}:
    print("main.py(): invalid output format: {}; exit."
          "".format(arguments.write), file = sys.stderr);
    sys.exit(1);

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

  if arguments.score is not None:
    normalize = ["anchors", "edges"];
  else:
    normalize = [];
    for action in arguments.normalize:
      if action in {"anchors", "edges"}:
        normalize.append(action);
      else:
        print("main.py(): invalid type of normalization: {}; exit."
              "".format(action), file = sys.stderr);
        sys.exit(1);

  graphs = read_graphs(arguments.input, format = arguments.read,
                       full = arguments.full, normalize = normalize,
                       reify = arguments.reify, text = text,
                       id = arguments.id, n = arguments.n, i = arguments.i);
  if not graphs:
    print("main.py(): unable to read input graph; exit.", file = sys.stderr);
    sys.exit(1);

  validate = [];
  for action in arguments.validate:
    if action in {"edges"}:
      validate.append(action);
    else:
      print("main.py(): invalid type of validation: {}; exit."
            "".format(action), file = sys.stderr);
      sys.exit(1);

  if validate:
    for graph in graphs:
      graph.validate(validate);

  if arguments.analyze:
    analyze(graphs);

  if arguments.gold and arguments.score:
    if arguments.format is None: arguments.format = arguments.read;
    gold = read_graphs(arguments.gold, format = arguments.format,
                       full = arguments.full, normalize = normalize,
                       reify = arguments.reify, text = text);
    if not gold:
      print("main.py(): unable to read gold graphs: {}; exit.", file = sys.stderr);
      sys.exit(1);
    for metric in arguments.score.split(","):
      result = None;
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
                                       trace = arguments.trace);
      elif metric == "ucca":
        result = score.ucca.evaluate(gold, graphs,
                                     format = arguments.write,
                                     trace = arguments.trace);

      if result is not None:
        if arguments.write == "json" or True:
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
    if arguments.write == "mrp":
      json.dump(graph.encode(), arguments.output,
                indent = None, ensure_ascii = False);
      print(file = arguments.output);
    elif arguments.write == "dot":
      graph.dot(arguments.output, arguments.strings);
      print(file = arguments.output);
    elif arguments.write == "txt":
      print("{}\t{}".format(graph.id, graph.input), file = arguments.output);
    elif arguments.write == "id":
      print("{}".format(graph.id), file = arguments.output);


if __name__ == "__main__":
  main();
