.PHONY: dm.edm.json eds.edm.json eds.smatch.json eds.mrp.json \
	dm.sdp.json peking.sdp.json peking.smatch.json peking.mrp.json \
	ucca.ucca.json ucca.smatch.json ucca.mrp.json \
	test.smatch.json coli.smatch.json coli.mrp.json \
	clean oe all

TRACE ?= --trace --trace

dm.edm.json:
	time python3 -u ../../main.py $(TRACE) --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/dm/wsj.mrp $@ 2>&1 | tee dm.edm.log

eds.edm.json:
	time python3 -u ../../main.py $(TRACE) --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp $@ 2>&1 | tee eds.edm.log

eds.smatch.json:
	time python3 -u ../../main.py $(TRACE) --score smatch \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp $@ 2>&1 | tee eds.smatch.log

eds.mrp.json:
	time python3 -u ../../main.py $(TRACE) --score mrp \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp $@ 2>&1 | tee eds.mrp.log

dm.sdp.json:
	time python3 -u ../../main.py $(TRACE) --score sdp \
	  --read mrp --gold ../sample/psd/wsj.mrp \
	  ../sample/dm/wsj.mrp $@ 2>&1 | tee dm.sdp.log

peking.sdp.json:
	time python3 -u ../../main.py $(TRACE) --score sdp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp $@ 2>&1 | tee peking.sdp.log

peking.smatch.json:
	time python3 -u ../../main.py $(TRACE) --score smatch --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp $@ 2>&1 | tee peking.smatch.log

peking.mrp.json:
	time python3 -u ../../main.py $(TRACE) --score mrp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp $@ 2>&1 | tee peking.mrp.log

ucca.ucca.json:
	time python3 -u ../../main.py --n 500 $(TRACE) --score ucca \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp $@ 2>&1 | tee ucca.ucca.log

ucca.smatch.json:
	time python3 -u ../../main.py --n 500 $(TRACE) --score smatch \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp $@ 2>&1 | tee ucca.smatch.log

ucca.mrp.json:
	time python3 -u ../../main.py --n 500 $(TRACE) --score mrp \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp $@ 2>&1 | tee ucca.mrp.log

empty.mrp.json:
	time python3 -u ../../main.py $(TRACE) --score mrp \
	  --read mrp --gold dm/empty.gold.mrp \
	  dm/empty.peking.mrp $@ 2>&1 | tee empty.mrp.log

partial.mrp.json:
	time python3 -u ../../main.py $(TRACE) --score mrp \
	  --read mrp --gold amr/partial.gold.mrp \
	  amr/partial.system.mrp $@ 2>&1 | tee partial.mrp.log

test.smatch.json:
	time python3 -u ../../main.py $(TRACE) --score smatch --limit 50 \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr $@ 2>&1 | tee test.smatch.log

test.mrp.json:
	time python3 -u ../../main.py $(TRACE) --score mrp --limit 50 \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr $@ 2>&1 | tee test.mrp.log

coli.smatch.json:
	time python3 -u ../../main.py --n 500 $(TRACE) --score smatch \
	  --read amr --gold amr/coli.gold.amr \
	  amr/coli.system.amr $@ 2>&1 | tee coli.smatch.log

coli.mrp.json:
	time python3 -u ../../main.py --n 500 $(TRACE) --score mrp \
	  --read amr --gold amr/coli.gold.amr \
	  amr/coli.system.amr $@ 2>&1 | tee coli.mrp.log

clean:
	/bin/rm *.json *.log

oe:
	make -j 4 $$(egrep '^[a-z/.]*.json:' Makefile | sed 's/://');

unit: empty.mrp.json partial.mrp.json

all: dm.edm.json eds.edm.json eds.smatch.json eds.mrp.json \
     dm.sdp.json peking.sdp.json peking.smatch.json peking.mrp.json \
     ucca.ucca.json ucca.smatch.json ucca.mrp.json \
     empty.mrp.json test.smatch.json test.mrp.json \
     coli.smatch.json coli.mrp.json
