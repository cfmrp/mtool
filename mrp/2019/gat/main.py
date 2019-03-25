#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
from pathlib import Path;
import sys;

from analyzer import analyze;
from graph import Graph;

import codec.amr;
import codec.eds;
import codec.sdp;
import codec.ucca;

__author__ = "oe"
__version__ = "0.1"

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--analyze", action = "store_true");
  parser.add_argument("--normalize", action = "store_true");
  parser.add_argument("--full", action = "store_true");
  parser.add_argument("--reify", action = "store_true");
  parser.add_argument("--read", required = True);
  parser.add_argument("--write");
  parser.add_argument("--text");
  parser.add_argument("--i", type = int);
  parser.add_argument("--n", type = int);
  parser.add_argument("--id");
  parser.add_argument("input", nargs = "?",
                      type=argparse.FileType("r"), default = sys.stdin);
  parser.add_argument("output", nargs = "?",
                      type=argparse.FileType("w"), default = sys.stdout);
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

  graphs = None
  if arguments.read == "amr":
    graphs = codec.amr.read(arguments.input, arguments.full, arguments.normalize, arguments.reify, text);
  elif arguments.read in {"ccd", "dm", "pas", "psd", "sdp"}:
    graphs = codec.sdp.read(arguments.input, text = text);
  elif arguments.read == "eds":
    graphs = codec.eds.read(arguments.input, text = text);
  elif arguments.read == "ucca":
    graphs = codec.ucca.read(arguments.input, text = text);
  if not graphs:
    print("main.py(): invalid input format: {}; exit.".format(arguments.format), file=sys.stderr)
    sys.exit(1)
    
  if arguments.analyze:
    analyze(graphs);
    
  for i, graph in enumerate(graphs):
    if arguments.i != None and i != arguments.i: continue;
    if arguments.n != None and i >= arguments.n: sys.exit(0);
    if arguments.id != None and graph.id != arguments.id: continue;
    if arguments.write == "mrp":
      json.dump(graph.encode(), arguments.output, indent = None);
      print(file = arguments.output);
    elif arguments.write == "dot":
      graph.dot(arguments.output);
      print(file = arguments.output);
