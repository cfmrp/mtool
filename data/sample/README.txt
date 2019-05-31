
CoNLL 2019 Shared Task: Meaning Representation Parsing --- Sample Graphs

Version 0.9; April 9, 2019


Overview
========

This directory contains a collection of 89 sample graphs in the five framworks
represented in the task: AMR, DM, EDS, PSD, and UCCA.  The sentences are drawn
from Section 00 of (the Penn Treebank selection from) the venerable Wall Street
Journal (WSJ) Corpus.  We only include sentences for which all five graph banks
provide annotations.

The purpose of this sample data is twofold: (a) exemplify the uniform graph
representation format (serialized in JSON) adopted for the task and (b) enable
in-depth linguistic comparison across frameworks.

For general information on the file format, please see:

  http://mrp.nlpl.eu/index.php?page=4#format


Contents
========

The main contents in this release are the JSON files:

  $ ls -l */*.mrp
  -rw-r--r--. 1 oe oe 145935 Apr  8 00:11 amr/wsj.mrp
  -rw-r--r--. 1 oe oe 290495 Apr  8 00:12 dm/wsj.mrp
  -rw-r--r--. 1 oe oe 334885 Apr  8 00:13 eds/wsj.mrp
  -rw-r--r--. 1 oe oe 225669 Apr  8 00:14 psd/wsj.mrp
  -rw-r--r--. 1 oe oe 254101 Apr  9 16:07 ucca/wsj.mrp

Each file contains the 89 graphs in the intersection of all frameworks (87 in
the case for UCCA, for the time being).  These graph serializations are in what
is called the JSON Lines format, effectively a stream of JSON objects with line
breaks as the separator character between objects.

To ease human inspection of these graphs, this package also provides graphical
renderings of all graphs, as separate files (one per sentence) in the ‘dot/’
and ‘pdf/’ sub-directories for each framework.  These visualizations have been
created using the MRP graph toolkit, which will be released by mid-May 2019.


Known Limitations
=================

None, for the time being.


Release History
===============

[Version 0.9; April 9, 2018]

+ First release of sample graphs in five frameworks: AMR, DM, EDS, UCCA, and PSD.


Contact
=======

For questions or comments, please do not hesitate to email the task organizers
at: ‘mrp-organizers@nlpl.eu’.

Omri Abend
Jan Hajič
Daniel Hershcovich
Marco Kuhlmann
Stephan Oepen
Tim O'Gorman
Nianwen Xue
