mtool
=====

<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Flag_of_Switzerland.svg/240px-Flag_of_Switzerland.svg.png" width=20>&nbsp;**The Swiss Army Knife of Meaning Representation**

This repository provides software to support participants in the
shared task on [_Meaning Representation Parsing_ (MRP)](http://mrp.nlpl.eu)
at the
[2019 Conference on Computational Natural Language Learning](http://www.conll.org/2019) (CoNLL).
Please see the above task web site for additional background.

Scoring
-------

`mtool` implements the official MRP 2019 cross-framwork metric, as well as
a range of framework-specific graph similarity metrics, viz.

+ MCES (Maximum Common Edge Subgraph Isomorphism);
+ EDM (Elementary Dependency Match; [Dridan & Oepen, 2011](http://aclweb.org/anthology/W/W11/W11-2927.pdf));
+ SDP Labeled and Unlabeled Dependency F1 ([Oepen et al., 2015](http://aclweb.org/anthology/S/S14/S14-2008.pdf));
+ SMATCH Precision, Recall, and F1 ([Cai & Knight, 2013](http://www.aclweb.org/anthology/P13-2131));
+ UCCA Labeled and Unlabeled Dependency F1 ([Hershcovich et al., 2019](https://www.aclweb.org/anthology/S19-2001)).

```
./main.py --read mrp --score mces --gold data/sample/eds/wsj.mrp data/score/eds/wsj.pet.mrp
{"n": 87,
 "tops": {"g": 87, "s": 87, "c": 85, "p": 0.9770114942528736, "r": 0.9770114942528736, "f": 0.9770114942528736},
 "labels": {"g": 2500, "s": 2508, "c": 2455, "p": 0.9788676236044657, "r": 0.982, "f": 0.9804313099041533},
 "properties": {"g": 262, "s": 261, "c": 257, "p": 0.9846743295019157, "r": 0.9809160305343512, "f": 0.982791586998088},
 "anchors": {"g": 2500, "s": 2508, "c": 2430, "p": 0.9688995215311005, "r": 0.972, "f": 0.9704472843450479},
 "edges": {"g": 2432, "s": 2439, "c": 2319, "p": 0.95079950799508, "r": 0.9535361842105263, "f": 0.952165879696161},
 "all": {"g": 7781, "s": 7803, "c": 7546, "p": 0.9670639497629117, "r": 0.9697982264490426, "f": 0.9684291581108829}}
```
Albeit originally defined for one specific framework (EDS, DM and PSD, AMR, and UCCA, respectively),
the non-MCES metrics are to some degree applicable to other frameworks too: the unified MRP representation
of semantic graphs enables such cross-framework application, in principle, but this functionality
remains largely untested so far.

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

The ‘official’ cross-framework metric for the MRP 2019 shared task will be a generalization
of the framework-specific metrics, considering all applicable ‘pieces of information’ (i.e.
tuples representing basic structural elements) for each framework:

1. top nodes;
2. node labels;
3. node properties;
4. node anchoring;
5. directed edges;
6. edge labels; and
7. edge properties.

When comparing two graphs, node-to-node correspondences need to be established (via a
potentially approximative search) to maximize the aggregate, unweighted score of all of the tuple
types that apply for each specific framework.
Directed edges and edge labels, however, are always considered in conjunction.

Analytics
---------


Validation
----------


Conversion
----------

Among its options for format coversion, `mtool` supports output of graphs to the
[DOT language](https://www.graphviz.org/documentation/) for graph visualization, e.g.
```
./main.py --id 20001001 --read mrp --write dot data/sample/eds/wsj.mrp 20001001.dot
dot -Tpdf 20001001.dot > 20001001.pdf
```
