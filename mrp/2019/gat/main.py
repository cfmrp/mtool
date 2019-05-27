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
import score.sdp;
import score.smatch;

__author__ = "oe"
__version__ = "0.1"

def read_graphs(stream, format = None,
                full = False, normalize = False, reify = False,
                prefix = None, text = None):

  graphs = None;
  if format == "amr":
    graphs = codec.amr.read(stream, full = full, normalize = normalize,
                            reify = reify, text = text);
  elif format in {"ccd", "dm", "pas", "psd"}:
    graphs = codec.sdp.read(stream, framework = format, text = text);
  elif format == "eds":
    graphs = codec.eds.read(stream, reify = reify, text = text);
  elif format == "ucca":
    graphs = codec.ucca.read(stream, text = text, prefix = prefix);
  elif format == "conllu" or format == "ud":
    graphs = codec.conllu.read(stream, framework = format, text = text)
  elif format == "mrp":
    graphs = codec.mrp.read(stream)

  return graphs;

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--analyze", action = "store_true");
  parser.add_argument("--normalize", action = "store_true");
  parser.add_argument("--full", action = "store_true");
  parser.add_argument("--reify", action = "store_true");
  parser.add_argument("--strings", action = "store_true");
  parser.add_argument("--gold", type = argparse.FileType("r"));
  parser.add_argument("--format");
  parser.add_argument("--score");
  parser.add_argument("--read", required = True);
  parser.add_argument("--write");
  parser.add_argument("--text");
  parser.add_argument("--prefix");
  parser.add_argument("--i", type = int);
  parser.add_argument("--n", type = int);
  parser.add_argument("--id");
  parser.add_argument("--trace", action = "store_true");
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

  graphs = read_graphs(arguments.input, format = arguments.read,
                       full = arguments.full, normalize = arguments.normalize,
                       reify = arguments.reify, text = text);
  if not graphs:
    print("main.py(): invalid input format: {}; exit."
          "".format(arguments.read), file = sys.stderr);
    sys.exit(1);

  if arguments.analyze:
    analyze(graphs);

  if arguments.gold and arguments.score:
    if arguments.format == None: arguments.format = arguments.read;
    gold = read_graphs(arguments.gold, format = arguments.format,
                       full = arguments.full, normalize = arguments.normalize,
                       reify = arguments.reify, text = text);
    if not gold:
      print("main.py(): invalid gold format: {}; exit."
            "".format(arguments.read), file = sys.stderr);
      sys.exit(1);
    for metric in arguments.score.split(","):
      if metric == "edm":
        score.edm.evaluate(gold, graphs,
                           arguments.output, format = arguments.write);
      elif metric == "sdp":
        score.sdp.evaluate(gold, graphs,
                           arguments.output, format = arguments.write);
      elif metric == "smatch":
        score.smatch.evaluate(gold, graphs,
                              arguments.output, format = arguments.write,
                              trace = arguments.trace);
      else:  
        print("main.py(): invalid evaluation metric: {}; exit."
              "".format(arguments.score), file = sys.stderr);
        sys.exit(1);
    sys.exit(0);
      
  for i, graph in enumerate(graphs):
    if arguments.i != None and i != arguments.i: continue;
    if arguments.n != None and i >= arguments.n: sys.exit(0);
    if arguments.id != None and graph.id != arguments.id: continue;
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
