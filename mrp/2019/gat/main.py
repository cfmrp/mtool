#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
from pathlib import Path;
import sys;

from graph import Graph;

from read_amr import read_amr
from eds import read_eds
from sdp import read_sdp;
#from ucca import read_ucca;

__author__ = "oe"
__version__ = "0.1"

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--format", required = True);
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
  if arguments.format == "amr":
    graphs = read_amr(arguments.input);
  elif arguments.format in ["ccd", "dm", "pas", "psd", "sdp"]:
    graphs = read_sdp(arguments.input);
  elif arguments.format == "eds":
    graphs = read_eds(arguments.input);
  elif arguments.format == "ucca":
    graphs = read_ucca(arguments.input);
  if not graphs:
    print("Invalid format: {}".format(arguments.format), file=sys.stderr)
    sys.exit(1)
    
  for graph in graphs:
    json.dump(graph.encode(), arguments.output, indent = None);
    print(file = arguments.output);
