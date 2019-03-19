#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
import sys;

from analyzer import Graph, analyze

from eds import read_eds;

__author__ = "oe"
__version__ = "0.1"

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--format");
  parser.add_argument("input", nargs = "?",
                      type=argparse.FileType("r"), default = sys.stdin);
  parser.add_argument("output", nargs = "?",
                      type=argparse.FileType("w"), default = sys.stdout);
  arguments = parser.parse_args();

  graphs = read_eds(arguments.input);
  for graph in graphs:
    json.dump(graph.encode(), arguments.output, indent = None);
    print(file = arguments.output);
