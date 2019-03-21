#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
from pathlib import Path;
import sys;

from graph import Graph;

from amr import read_amr
from eds import read_eds
from sdp import read_sdp;
#from ucca import read_ucca;

__author__ = "oe"
__version__ = "0.1"

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--read", required = True);
  parser.add_argument("--write", default = "mrp");
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
    graphs = read_amr(arguments.input);
  elif arguments.read in ["ccd", "dm", "pas", "psd", "sdp"]:
    graphs = read_sdp(arguments.input);
  elif arguments.read == "eds":
    graphs = read_eds(arguments.input, text = text);
  elif arguments.read == "ucca":
    graphs = read_ucca(arguments.input);
  if not graphs:
    print("main.py(): invalid input format: {}; exit.".format(arguments.format), file=sys.stderr)
    sys.exit(1)
    
  for graph in graphs:
    if arguments.write == "mrp":
      json.dump(graph.encode(), arguments.output, indent = None);
      print(file = arguments.output);
    elif arguments.write == "dot":
      graph.dot(arguments.output);
