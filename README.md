mtool
=====
The Swiss Army Knife of Meaning Representation

This repository provides software to support participants in the
shared task on [_Meaning Representation Parsing_ (MRP)](http://mrp.nlpl.eu)
at the
[2019 Conference on Computational Natural Language Learning](http://www.conll.org/2019) (CoNLL).
Please see the above task web site for additional background.

Scoring
-------

`mtool` implements a range of framework-specific graph similarity metrics,
viz.

+ EDM (Elementary Dependency Match; [Dridan & Oepen, 2011](http://aclweb.org/anthology/W/W11/W11-2927.pdf));
+ SDP Labeled and Unlabeled Dependency F1 ([Oepen et al., 2015](http://aclweb.org/anthology/S/S14/S14-2008.pdf));
+ SMATCH ([Cai & Knight, 2013](http://www.aclweb.org/anthology/P13-2131));
+ UCCA Labeled and Unlabeled Dependency F1 (Hershcovich et al., 2019).

Albeit originally defined for one specific framework (EDS, DM and PSD, AMR, and UCCA, respectively),
these metrics are to some degree applicable to other frameworks too: the unified MRP representation
of semantic graphs enables such cross-framework application, in principle, but this functionality
remains largely untested so far.

The `Makefile` in the `data/score/` sub-directory shows some example calls for the MRP scorer.
Initially, it is recommend to score graphs in each framework using its ‘traditional’ metric, e.g.
```
 ../../main.py --read mrp --score ucca --gold ucca/ewt.gold.mrp ucca/ewt.tupa.mrp 
{'n': 3757,
 'labeled':
   {'primary': {'g': 63720, 's': 62876, 'c': 38195,
                'p': 0.6074654876264394, 'r': 0.5994193345888261, 'f': 0.6034155897500711},
    'remote': {'g': 2673, 's': 1259, 'c': 581,
               'p': 0.4614773629864972, 'r': 0.21735877291432848, 'f': 0.2955239064089522}},
 'unlabeled':
   {'primary': {'g': 56114, 's': 55761, 'c': 52522,
                'p': 0.9419128064417783, 'r': 0.9359874541112735, 'f': 0.938940782122905},
    'remote': {'g': 2629, 's': 1248, 'c': 595,
               'p': 0.47676282051282054, 'r': 0.22632179535945227, 'f': 0.3069383543977302}}}
```

The ‘official’ cross-framework metric for the MRP 2019 shared task will be a generalization
of the framework-specific metrics, considering all applicable ‘pieces of information’ (i.e.
tuples representing basic structural elements) for each framework:

1. top nodes;
2. node labels;
3. node properties;
4. node anchoring;
5. edges;
6. edge labels; and
7. edge properties.

When comparing two graphs, node-to-node correspondences will be established (via an
approximative search) to maximize the aggregate, unweighted score of all of the tuple
types that apply for each specific framework.

Analytics
---------


Validation
----------


Conversion
----------
