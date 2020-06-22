#!/usr/bin/env python3

# -*- coding: utf-8; -*-

import argparse;
import json;
import multiprocessing as mp;
import re;
import sys;
import time;
from pathlib import Path;
from zipfile import ZipFile;

import codec.amr;
import codec.conllu;
import codec.eds;
import codec.mrp;
import codec.pmb;
import codec.sdp;
import codec.treex;
import codec.ucca;
import inspector;
import score.edm;
import score.mces;
import score.sdp;
import score.smatch;
import score.ucca;
import validate.core;
from analyzer import analyze;

__author__ = "oe"

ENCODING = "utf-8";
NORMALIZATIONS = {"anchors", "case", "edges", "attributes"};
VALIDATIONS = {"input", "anchors", "edges",
               "amr", "eds", "sdp", "ucca"}

def read_graphs(stream, format = None,
                full = False, normalize = False, reify = False,
                frameworks = None, prefix = None, text = None,
                trace = 0, strict = 0, quiet = False, robust = False,
                alignment = None, anchors = None, pretty = False,
                id = None, n = None, i = None):

  name = getattr(stream, "name", "");
  if name.endswith(".zip"):
    with ZipFile(name) as zip:
      stream = None;
      for entry in zip.namelist():
        if entry.endswith(".mrp"):
          if stream is not None:
            print("read_graphs(): multiple MRP entries in ‘{}’; exit."
                  "".format(name), file = sys.stderr);
            sys.exit(1);
          stream = zip.open(entry);
      if stream is None:
        print("read_graphs(): missing MRP entry in ‘{}’; exit."
              "".format(name), file = sys.stderr);
        sys.exit(1);

  generator = None;
  if format in {"amr", "camr"}:
    generator \
      = codec.amr.read(stream, full = full, reify = reify,
                       text = text, camr = format == "camr",
                       alignment = alignment, quiet = quiet, trace = trace);
  elif format in {"ccd", "dm", "pas", "psd"}:
    generator = codec.sdp.read(stream, framework = format, text = text);
  elif format == "eds":
    generator = codec.eds.read(stream, reify = reify, text = text);
  elif format == "mrp":
    generator = codec.mrp.read(stream, text = text, robust = robust);
  elif format == "pmb":
    generator = codec.pmb.read(stream, full = full,
                               reify = reify, text = text,
                               trace = trace, strict = strict);
  elif format == "treex":
    generator = codec.treex.read(stream)
  elif format == "ucca":
    generator = codec.ucca.read(stream, text = text, prefix = prefix);
  elif format == "conllu" or format == "ud":
    generator = codec.conllu.read(stream, framework = format, text = text,
                                  anchors = anchors, trace = trace);
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
      if frameworks is not None and graph.framework not in frameworks: continue;
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
    except Exception as error:
      print(error, file = sys.stderr);
      pass;

  if pretty:
    for graph in graphs: graph.prettify(trace);
  if normalize:
    for graph in graphs: graph.normalize(normalize, trace);

  return graphs, overlays;

def main():
  parser = argparse.ArgumentParser(description = "MRP Graph Toolkit");
  parser.add_argument("--inspect", action = "store_true");
  parser.add_argument("--analyze", action = "store_true");
  parser.add_argument("--normalize", action = "append", default = []);
  parser.add_argument("--full", action = "store_true");
  parser.add_argument("--reify", action = "store_true");
  parser.add_argument("--unique", action = "store_true");
  parser.add_argument("--ids", action = "store_true");
  parser.add_argument("--strings", action = "store_true");
  parser.add_argument("--framework", action = "append", default = []);
  parser.add_argument("--gold",
                      type = argparse.FileType("r", encoding = ENCODING));
  parser.add_argument("--alignment",
                      type = argparse.FileType("r", encoding = ENCODING));
  parser.add_argument("--overlay",
                      type = argparse.FileType("w", encoding = ENCODING));
  parser.add_argument("--format");
  parser.add_argument("--score");
  parser.add_argument("--validate", action = "append", default = []);
  parser.add_argument("--limit");
  parser.add_argument("--read", required = True);
  parser.add_argument("--write");
  parser.add_argument("--text");
  parser.add_argument("--anchors",
                      type = argparse.FileType("r", encoding = ENCODING));
  parser.add_argument("--prefix");
  parser.add_argument("--source");
  parser.add_argument("--pretty", action = "store_true");
  parser.add_argument("--inject");
  parser.add_argument("--version", type = float, default = 1.1);
  parser.add_argument("--cores", type = int, default = 1);
  parser.add_argument("--i", type = int);
  parser.add_argument("--n", type = int);
  parser.add_argument("--id");
  parser.add_argument("--quiet", action = "store_true");
  parser.add_argument("--robust", action = "store_true");
  parser.add_argument("--trace", "-t", action = "count", default = 0);
  parser.add_argument("--strict", action = "count", default = 0);
  parser.add_argument("--errors",
                      type = argparse.FileType("w", encoding = ENCODING));
  parser.add_argument("input", nargs = "?",
                      type = argparse.FileType("r", encoding = ENCODING),
                      default = sys.stdin);
  parser.add_argument("output", nargs = "?",
                      type = argparse.FileType("w", encoding = ENCODING),
                      default = sys.stdout);
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
                            "ccd", "dm", "pas", "psd", "treex",
                            "eds", "ucca",
                            "amr", "camr", "pmb",
                            "conllu", "ud"}:
    print("main.py(): invalid input format: {}; exit."
          "".format(arguments.read), file = sys.stderr);
    sys.exit(1);

  if arguments.write is not None and \
     arguments.write not in {"dot", "evaluation", "id", "json", "mrp", "txt", "ucca"}:
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
                              "amr", "camr", "pmb",
                              "conllu", "ud"}:
    print("main.py(): invalid gold format: {}; exit."
          "".format(arguments.read), file = sys.stderr);
    sys.exit(1);

  if len(arguments.normalize) == 1 and arguments.normalize[0] == "all":
    normalize = NORMALIZATIONS;
  else:
    normalize = set();
    for action in arguments.normalize:
      if action in NORMALIZATIONS:
        normalize.add(action);
      else:
        print("main.py(): invalid type of normalization: {}; exit."
              "".format(action), file = sys.stderr);
        sys.exit(1);
  if arguments.score is not None and len(normalize) == 0:
    normalize = NORMALIZATIONS;

  if arguments.alignment is not None and arguments.overlay is None:
    print("main.py(): option ‘--alignment’ requires ‘--overlay’; exit.",
          file = sys.stderr);
    sys.exit(1);

  if len(arguments.framework) == 0: arguments.framework = None;

  if arguments.cores == 0: arguments.cores = mp.cpu_count();
    
  graphs, overlays \
    = read_graphs(arguments.input, format = arguments.read,
                  full = arguments.full, normalize = normalize,
                  reify = arguments.reify, frameworks = arguments.framework,
                  text = text, alignment = arguments.alignment,
                  anchors = arguments.anchors, pretty = arguments.pretty,
                  trace = arguments.trace, strict = arguments.strict,
                  quiet = arguments.quiet, robust = arguments.robust,
                  id = arguments.id, n = arguments.n, i = arguments.i);
  if graphs is None:
    print("main.py(): unable to read input graphs: {}; exit."
          "".format(arguments.input.name), file = sys.stderr);
    sys.exit(1);

  if arguments.unique:
    unique = list();
    ids = set();
    for graph in graphs:
      id = graph.id;
      if id not in ids:
        ids.add(id);
        unique.append(graph);
    graphs = unique;

  #
  # inject any additional information provided on the command line
  #
  if arguments.source:
    for graph in graphs: graph.source(arguments.source);
  if arguments.inject:
    for graph in graphs: graph.inject(arguments.inject);

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

  if arguments.quiet: arguments.trace = 0;

  if actions:
    for graph in graphs:
      validate.core.test(graph, actions, stream = sys.stderr);

  if arguments.analyze:
    analyze(graphs);

  gold = None;
  if arguments.gold and arguments.score or arguments.inspect:
    if arguments.format is None: arguments.format = arguments.read;
    gold, _ = read_graphs(arguments.gold, format = arguments.format,
                          full = arguments.full, normalize = normalize,
                          reify = arguments.reify, frameworks = arguments.framework,
                          text = text, trace = arguments.trace,
                          quiet = arguments.quiet, robust = arguments.robust,
                          id = arguments.id, n = arguments.n, i = arguments.i);
    if gold is None:
      print("main.py(): unable to read gold graphs: {}; exit."
            "".format(arguments.gold.name), file = sys.stderr);
      sys.exit(1);

  if arguments.inspect:
    result = inspector.summarize(graphs, gold);
    if arguments.write == "json" or True:
      json.dump(result, arguments.output, indent = None);
      print(file = arguments.output);
    sys.exit(0);

  if arguments.score:
    limits = {"rrhc": None, "mces": None};
    for metric in arguments.score.split(","):
      if arguments.limit is not None:
        try:
          match = re.search(r"([0-9]+):([0-9]+)", arguments.limit)
          if match:
            limits["rrhc"] = int(match.group(1));
            limits["mces"] = int(match.group(2));
          else:
            if metric == "smatch":
              limits["rrhc"] = int(arguments.limit);
            else:
              limits["mces"] = int(arguments.limit);
        except:
          print("main.py(): invalid ‘--limit’ {}; exit.".format(arguments.limit),
                file = sys.stderr);
          sys.exit(1);
      errors = dict() if arguments.errors else None;
      result = None;
      launch = time.time(), time.process_time();
      if metric == "edm":
        result = score.edm.evaluate(gold, graphs,
                                    format = arguments.write,
                                    trace = arguments.trace);
      elif metric == "mrp":
        result = score.mces.evaluate(gold, graphs,
                                     format = arguments.write,
                                     limits = limits,
                                     cores = arguments.cores,
                                     trace = arguments.trace,
                                     errors = errors,
                                     quiet = arguments.quiet);
      elif metric == "sdp":
        result = score.sdp.evaluate(gold, graphs,
                                    format = arguments.write,
                                    trace = arguments.trace);
      elif metric == "smatch":
        result = score.smatch.evaluate(gold, graphs,
                                       format = arguments.write,
                                       limit = limits["rrhc"],
                                       values = {"tops", "labels",
                                                 "properties", "anchors",
                                                 "edges", "attributes"},
                                       trace = arguments.trace);
      elif metric == "ucca":
        result = score.ucca.evaluate(gold, graphs,
                                     format = arguments.write,
                                     trace = arguments.trace);

      if result is not None:
        result["time"] = time.time() - launch[0];
        result["cpu"] = time.process_time() - launch[1];
        if arguments.write == "json" or True:
          #
          # _fix_me_
          # we should write a genuine custom JSON encoder
          #
          print("{", file = arguments.output, end = "");
          start = True;
          for key in result:
            if start: start = False;
            else: print(",\n ", file = arguments.output, end = "");
            print("\"{}\": ".format(key), file = arguments.output, end = "");
            json.dump(result[key], arguments.output, indent = None);
          print("}", file = arguments.output);

      if errors is not None:
        if arguments.write == "dot":
          for graph in gold:
            graph.dot(arguments.errors,
                      ids = arguments.ids, strings = arguments.strings,
                      errors = errors[graph.framework][graph.id]);
        elif arguments.write == "json" or True:
          json.dump(errors, arguments.errors, indent = None);
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
      json.dump(graph.encode(arguments.version), arguments.output,
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
    elif arguments.write == "ucca":
      # Prints everything to one long file. To split to separate XML files, use, e.g.,
      # csplit -zk output.xml '/^<root/' -f '' -b '%02d.xml' {99}
      codec.ucca.write(graph, graph.input, file = arguments.output)
  if arguments.overlay:
    for graph in overlays:
      if graph:
        json.dump(graph.encode(arguments.version), arguments.overlay,
                  indent = None, ensure_ascii = False);
        print(file = arguments.overlay);
    
if __name__ == "__main__":
  main();
