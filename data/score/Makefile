.PHONY: dm.edm.json eds.edm.json eds.smatch.json eds.mrp.json \
	dm.sdp.json peking.sdp.json peking.smatch.json peking.mrp.json \
	ucca.ucca.json ucca.smatch.json ucca.mrp.json \
	test.smatch.json coli.smatch.json coli.mrp.json \
	all

dm.edm.json:
	time python3 -u ../../main.py --trace --trace --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/dm/wsj.mrp $@ 2>&1 | tee -a dm.edm.log

eds.edm.json:
	time python3 -u ../../main.py --trace --trace --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp $@ 2>&1 | tee -a eds.edm.log

eds.smatch.json:
	time python3 -u ../../main.py --trace --trace --score smatch \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp $@ 2>&1 | tee -a eds.smatch.log

eds.mrp.json:
	time python3 -u ../../main.py --trace --trace --score mrp \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp $@ 2>&1 | tee -a eds.mrp.log

dm.sdp.json:
	time python3 -u ../../main.py --trace --trace --score sdp \
	  --read mrp --gold ../sample/psd/wsj.mrp \
	  ../sample/dm/wsj.mrp $@ 2>&1 | tee -a dm.sdp.log

peking.sdp.json:
	time python3 -u ../../main.py --trace --trace --score sdp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp $@ 2>&1 | tee -a peking.sdp.log

peking.smatch.json:
	time python3 -u ../../main.py --trace --trace --score smatch --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp $@ 2>&1 | tee -a peking.smatch.log

peking.mrp.json:
	time python3 -u ../../main.py --trace --trace --score mrp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp $@ 2>&1 | tee -a peking.mrp.log

ucca.ucca.json:
	time python3 -u ../../main.py --trace --trace --score ucca \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp $@ 2>&1 | tee -a ucca.ucca.log

ucca.smatch.json:
	time python3 -u ../../main.py --trace --trace --score smatch \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp $@ 2>&1 | tee -a ucca.smatch.log
ucca.mrp.json:
	time python3 -u ../../main.py --trace --trace --score mrp \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp $@ 2>&1 | tee -a ucca.mrp.log

test.smatch.json:
	time python3 -u ../../main.py --trace --trace --score smatch --limit 50 \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr $@ 2>&1 | tee -a test.smatch.log

coli.smatch.json:
	time python3 -u ../../main.py --trace --trace --score smatch \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr $@ 2>&1 | tee -a coli.smatch.log

coli.mrp.json:
	time python3 -u ../../main.py --trace --trace --score mrp \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr $@ 2>&1 | tee -a coli.smatch.log

all:
	make -j 4 $$(egrep '^[a-z/.]*.json:' Makefile | grep -v all: | sed 's/://');
