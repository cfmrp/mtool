.PHONY: dm/edm eds/edm dm/sdp peking/sdp \
	ucca/ucca test/smatch coli/smatch \
	eds/mrp eds/smatch

dm/edm:
	time ../../main.py --trace --trace --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/dm/wsj.mrp 2>&1 | tee -a dm.edm.log

eds/edm:
	time ../../main.py --trace --trace --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp 2>&1 | tee -a eds.edm.log

eds/smatch:
	time ../../main.py --trace --trace --score smatch \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp 2>&1 | tee -a eds.smatch.log

eds/mrp:
	time ../../main.py --trace --trace --score mrp \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  eds/wsj.pet.mrp 2>&1 | tee -a eds.mrp.log

dm/sdp:
	time ../../main.py --trace --trace --score sdp \
	  --read mrp --gold ../sample/psd/wsj.mrp \
	  ../sample/dm/wsj.mrp 2>&1 | tee -a dm.sdp.log

peking/sdp:
	time ../../main.py --trace --trace --score sdp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp 2>&1 | tee -a peking.sdp.log

peking/smatch:
	time ../../main.py --trace --trace --score smatch --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp 2>&1 | tee -a peking.smatch.log

peking/mrp:
	time ../../main.py --trace --trace --score mrp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp 2>&1 | tee -a peking.mrp.log

ucca/ucca:
	time ../../main.py --trace --trace --score ucca \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp 2>&1 | tee -a ucca.ucca.log

ucca/smatch:
	time ../../main.py --trace --trace --score smatch \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp 2>&1 | tee -a ucca.smatch.log
ucca/mrp:
	time ../../main.py --trace --trace --score mrp \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp 2>&1 | tee -a ucca.mrp.log

test/smatch:
	time ../../main.py --trace --trace --score smatch --limit 50 \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr 2>&1 | tee -a test.smatch.log

coli/smatch:
	time ../../main.py --trace --trace --score smatch \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr 2>&1 | tee -a coli.smatch.log

coli/mrp:
	time ../../main.py --trace --trace --score mrp \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr 2>&1 | tee -a coli.smatch.log
