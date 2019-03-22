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
  parser.add_argument("--read", required = True);
  parser.add_argument("--write");
  parser.add_argument("--text");
  parser.add_argument("input", nargs = "?",
                      type=argparse.FileType("r"), default = sys.stdin);
  parser.add_argument("output", nargs = "?",
                      type=argparse.FileType("w"), default = sys.stdout);
  arguments = parser.parse_args();

  text = None;
  if arguments.text and Path(arguments.text).is_dir():
    text = Path(arguments.text);
    

  graphs = None
  if arguments.read == "amr":
    graphs = codec.amr.read(arguments.input);
  elif arguments.read in ["ccd", "dm", "pas", "psd", "sdp"]:
    graphs = codec.sdp.read(arguments.input);
  elif arguments.read == "eds":
    graphs = codec.eds.read(arguments.input, text = text);
  elif arguments.read == "ucca":
    graphs = codec.ucca.read(arguments.input);
  if not graphs:
    print("main.py(): invalid input format: {}; exit.".format(arguments.format), file=sys.stderr)
    sys.exit(1)
    
  if arguments.analyze:
    analyze(graphs);
    
  for graph in graphs:
    if arguments.write == "mrp":
      json.dump(graph.encode(), arguments.output, indent = None);
      print(file = arguments.output);
    elif arguments.write == "dot":
      graph.dot(arguments.output);
