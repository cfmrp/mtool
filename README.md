mtool
=====

<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Flag_of_Switzerland.svg/240px-Flag_of_Switzerland.svg.png" width=20>&nbsp;**The Swiss Army Knife of Meaning Representation**

This repository provides software to support participants in the
shared task on [Meaning Representation Parsing (MRP)](http://mrp.nlpl.eu)
at the
[2019 Conference on Computational Natural Language Learning](http://www.conll.org/2019) (CoNLL).
Please see the above task web site for additional background.

Scoring
-------

`mtool` implements the official MRP 2019 cross-framwork metric, as well as
a range of framework-specific graph similarity metrics, viz.

+ MRP (Maximum Common Edge Subgraph Isomorphism);
+ EDM (Elementary Dependency Match; [Dridan & Oepen, 2011](http://aclweb.org/anthology/W/W11/W11-2927.pdf));
+ SDP Labeled and Unlabeled Dependency F1 ([Oepen et al., 2015](http://aclweb.org/anthology/S/S14/S14-2008.pdf));
+ SMATCH Precision, Recall, and F1 ([Cai & Knight, 2013](http://www.aclweb.org/anthology/P13-2131));
+ UCCA Labeled and Unlabeled Dependency F1 ([Hershcovich et al., 2019](https://www.aclweb.org/anthology/S19-2001)).

The ‘official’ cross-framework metric for the MRP 2019 shared task is a generalization
of the framework-specific metrics, considering all applicable ‘pieces of information’ (i.e.
tuples representing basic structural elements) for each framework:

1. top nodes;
2. node labels;
3. node properties;
4. node anchoring;
5. directed edges;
6. edge labels; and
7. edge attributes.

When comparing two graphs, node-to-node correspondences need to be established (via a
potentially approximative search) to maximize the aggregate, unweighted score of all of the tuple
types that apply for each specific framework.
Directed edges and edge labels, however, are always considered in conjunction during
this search.
```
./main.py --read mrp --score mrp --gold data/sample/eds/wsj.mrp data/score/eds/wsj.pet.mrp
{"n": 87,
 "tops": {"g": 87, "s": 87, "c": 85, "p": 0.9770114942528736, "r": 0.9770114942528736, "f": 0.9770114942528736},
 "labels": {"g": 2500, "s": 2508, "c": 2455, "p": 0.9788676236044657, "r": 0.982, "f": 0.9804313099041533},
 "properties": {"g": 262, "s": 261, "c": 257, "p": 0.9846743295019157, "r": 0.9809160305343512, "f": 0.982791586998088},
 "anchors": {"g": 2500, "s": 2508, "c": 2430, "p": 0.9688995215311005, "r": 0.972, "f": 0.9704472843450479},
 "edges": {"g": 2432, "s": 2439, "c": 2319, "p": 0.95079950799508, "r": 0.9535361842105263, "f": 0.952165879696161},
 "attributes": {"g": 0, "s": 0, "c": 0, "p": 0.0, "r": 0.0, "f": 0.0},
 "all": {"g": 7781, "s": 7803, "c": 7546, "p": 0.9670639497629117, "r": 0.9697982264490426, "f": 0.9684291581108829}}
```
Albeit originally defined for one specific framework (EDS, DM and PSD, AMR, or UCCA, respectively),
the pre-MRP metrics are to some degree applicable to other frameworks too: the unified MRP representation
of semantic graphs enables such cross-framework application, in principle, but this functionality
remains largely untested (as of June 2019).

The `Makefile` in the `data/score/` sub-directory shows some example calls for the MRP scorer.
As appropriate (e.g. for comparison to third-party results), it is possible to score graphs in
each framework using its ‘own’ metric, for example (for AMR and UCCA, respectively):
```
./main.py --read mrp --score smatch --gold data/score/amr/test1.mrp data/score/amr/test2.mrp 
{"n": 3, "g": 30, "s": 29, "c": 24, "p": 0.8, "r": 0.8275862068965517, "f": 0.8135593220338982}
```

```
./main.py --read mrp --score ucca --gold data/score/ucca/ewt.gold.mrp data/score/ucca/ewt.tupa.mrp 
{"n": 3757,
 "labeled":
   {"primary": {"g": 63720, "s": 62876, "c": 38195,
                "p": 0.6074654876264394, "r": 0.5994193345888261, "f": 0.6034155897500711},
    "remote": {"g": 2673, "s": 1259, "c": 581,
               "p": 0.4614773629864972, "r": 0.21735877291432848, "f": 0.2955239064089522}},
 "unlabeled":
   {"primary": {"g": 56114, "s": 55761, "c": 52522,
                "p": 0.9419128064417783, "r": 0.9359874541112735, "f": 0.938940782122905},
    "remote": {"g": 2629, "s": 1248, "c": 595,
               "p": 0.47676282051282054, "r": 0.22632179535945227, "f": 0.3069383543977302}}}
```

For all scorers, the `--trace` command-line option will enable per-item scores in the result
(indexed by graph identifiers).
For MRP and SMATCH, the `--limit` option controls the maximum node pairing steps or
hill-climbing iterations, respectively, to attempt during the search (with defaults `500000`
and `20`, respectively).
As of early July, 2019, the search for none-to-node correspondences in the MRP metric can be
initialized from the result of the random-restart hill-climbing (RRHC) search from SMATCH.
This initialization is on by default; it increases running time of the MRP scorer but yields
a guarantee that the `"all"` counts of matching tuples in MRP will always be at least as
high as the number of `"c"`(orrect) tuples identified by SMATCH.
To control the two search steps in MRP computation separately, the `--limit` option can
take a colon-separated pair of integers, for example `5:100000` for five hill-climbing
iterations and up to 100,000 node pairing steps.
Note that multi-valued use of the `--limit` option is only meaningful in conjunction
with the MRP metric, and that setting either of the two values to `0` will disable the
corresponding search component.
Finally, the MRP scorer can parallelize evaluation: an option like `--cores 8` (on
suitable hardware) will run eight `mtool` processes in parallel, which should reduce
scoring time substantially.

Analytics
---------

[Kuhlmann & Oepen (2016)](http://www.mitpressjournals.org/doi/pdf/10.1162/COLI_a_00268) discuss a range of structural graph statistics; `mtool` integrates their original code, e.g.
```
./main.py --read mrp --analyze data/sample/amr/wsj.mrp 
(01)	number of graphs	87
(02)	number of edge labels	52
(03)	\percentgraph\ trees	51.72
(04)	\percentgraph\ treewidth one	51.72
(05)	average treewidth	1.494
(06)	maximal treewidth	3
(07)	average edge density	1.050
(08)	\percentnode\ reentrant	4.24
(09)	\percentgraph\ cyclic	13.79
(10)	\percentgraph\ not connected	0.00
(11)	\percentgraph\ multi-rooted	0.00
(12)	percentage of non-top roots	0.00
(13)	average edge length	--
(14)	\percentgraph\ noncrossing	--
(15)	\percentgraph\ pagenumber two	--
```

Validation
----------

`mtool` can test high-level wellformedness and (superficial) plausiblity of MRP
graphs through its emerging `--validate` option.
The MRP validator continues to evolve, but the following is indicative of its
functionality:
```
./main.py --read mrp --validate all data/validate/eds/wsj.mrp 
validate(): graph ‘20001001’: missing or invalid ‘input’ property
validate(): graph ‘20001001’; node #0: missing or invalid label
validate(): graph ‘20001001’; node #1: missing or invalid label
validate(): graph ‘20001001’; node #3: missing or invalid anchoring
validate(): graph ‘20001001’; node #6: invalid ‘anchors’ value: [{'from': 15, 'to': 23}, {'from': 15, 'to': 23}]
validate(): graph ‘20001001’; node #7: invalid ‘anchors’ value: [{'form': 15, 'to': 17}]
```

Conversion
----------

Among its options for format coversion, `mtool` supports output of graphs to the
[DOT language](https://www.graphviz.org/documentation/) for graph visualization, e.g.
```
./main.py --id 20001001 --read mrp --write dot data/sample/eds/wsj.mrp 20001001.dot
dot -Tpdf 20001001.dot > 20001001.pdf
```
When converting from token-based file formats that may lack either the underlying
‘raw’ input string, character-based anchoring, or both, the `--text` command-line
option will enable recovery of inputs and attempt to determine anchoring.
Its argument must be a file containing pairs of identifiers and input strings, one
per line, separated by a tabulator, e.g.
```
./main.py --id 20012005 --text data/sample/wsj.txt --read dm --write dot data/sample/psd/wsj.sdp 20012005.dot
```
For increased readability, the `--ids` option will include MRP node identifiers
in graph rendering, and the `--strings` option can replace character-based
anchors with the corresponding sub-string from the `input` field of the graph
(currently only for the DOT output format), e.g.
```
./main.py --n 1 --strings --read mrp --write dot data/sample/ucca/wsj.mrp vinken.dot
```

Diagnostics
--------------

When scoring with the MRP metric, `mtool` can optionally provide a per-item
breakdown of differences between the gold and the system graphs, i.e. record
false negatives (‘missing’ tuples) and false positives (‘surplus’ ones).
This functionality is activated via the `--errors` command-line option, and
tuple mismatches between the two graphs are recorded as a hierarchically
nested JSON object, indexed (in order) by framework, item identifier, and tuple
type.

For example:
```
./main.py --read mrp --score mrp --framework eds --gold data/score/lpps.mrp --errors errors.json data/score/eds/lpps.peking.mrp
```
For the first EDS item (`#102990`) in this comparison, `errors.json` will
contain a sub-structure like the following:
```
{"correspondences": [[0, 0], [1, 1], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11],
                     [11, 12], [12, 13], [13, 15], [14, 16], [15, 17], [16, 14], [17, 18], [18, 19], [19, 20]],
 "labels": {"missing": [[2, "_very+much_a_1"]],
            "surplus": [[3, "_much_x_deg"], [2, "_very_x_deg"]]},
 "anchors": {"missing": [[2, [6, 7, 8, 9, 11, 12, 13, 14]]],
             "surplus": [[2, [6, 7, 8, 9]], [3, [11, 12, 13, 14]]]},
 "edges": {"surplus": [[2, 3, "arg1"]]}}
```
When interpreting this structure, there are (of course) two separate spaces of
node identifiers; the `correspondences` vector records the (optimal)
node-to-node relation found by the MRP scorer, pairing identifiers from the
*gold* graph with corresponding identifiers in the *system* graph.
In the above, for example, gold node `#2` corresponds to system node `#3`,
and there is a spurious node `#2` in the example system graph, which
does not correspond to any of the gold nodes.
Node identifiers in `"missing"` entries refer to gold nodes, whereas
identifiers in `"surplus"` entries refer to the system graph, and they may
or may not stand in a correspondence relation to a gold node.

The differences between these two graphs can be visualized as follows, color-coding
false negatives in red, and false positives in blue
(and using gold identifiers, where available).

![sample visualization](https://github.com/cfmrp/mtool/blob/master/data/score/eds/lpps.102990.png)

Common Options
--------------

The `--read` and `--write` command-line options determine the input and output
codecs to use.
Valid input arguments include `mrp`, `amr`, `ccd`, `dm`, `eds`, `pas`, `psd`, `ud`,
and `ucca`; note that some of these formats are only [partially supported](https://github.com/cfmrp/mtool/issues).
The range of supported output codecs includes `mrp`, `dot`, or `txt`.

The optional `--id`, `--i`, or `--n` options control which graph(s)
from the input file(s) to process, selecting either by identifier, by (zero-based)
position into the sequence of graphs read from the file, or using the first _n_
graphs.
These options cannot be combined with each other and take precendence over each
other in the above order.

Installation
------------

You can install `mtool` via `pip` with the following command:

```
pip install git+https://github.com/cfmrp/mtool.git#egg=mtool
```

Authors
-------

+ Daniel Hershcovich <daniel.hershcovich@gmail.com> (@danielhers)
+ Marco Kuhlmann <marco.kuhlmann@liu.se> (@khlmnn)
+ Stephan Oepen <oe@ifi.uio.no> (@oepen)
+ Tim O'Gorman <timjogorman@gmail.com> (@timjogorman)

Contributors
------------

+ Yuta Koreeda <koreyou@mac.com> (@koreyou)
+ Matthias Lindemann <mlinde@coli.uni-saarland.de> (@namednil)
+ Hiroaki Ozaki <taryou.ozk@gmail.com> (@taryou)
+ Milan Straka <straka@ufal.mff.cuni.cz> (@foxik)

[![Build Status (Travis CI)](https://travis-ci.org/cfmrp/mtool.svg?branch=master)](https://travis-ci.org/cfmrp/mtool)
[![Build Status (AppVeyor)](https://ci.appveyor.com/api/projects/status/github/cfmrp/mtool?svg=true)](https://ci.appveyor.com/project/danielh/mtool)
