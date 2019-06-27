.PHONY: dm/edm eds/edm dm/sdp peking/sdp \
	ucca/ucca test/smatch coli/smatch \
	eds/mrp eds/smatch

dm/edm:
	time ../../main.py --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/dm/wsj.mrp 2>&1 | tee -adm.edm.log

eds/edm:
	time ../../main.py --score edm \
	  --format mrp --gold ../sample/eds/wsj.mrp \
	  --read eds eds/wsj.pet.eds 2>&1 | tee -aeds.edm.log

eds/smatch:
	time ../../main.py --score smatch \
	  --format mrp --gold ../sample/eds/wsj.mrp \
	  --read eds eds/wsj.pet.eds 2>&1 | tee -aeds.smatch.log

eds/mrp:
	time ../../main.py --score mrp \
	  --format mrp --gold ../sample/eds/wsj.mrp \
	  --read eds eds/wsj.pet.eds 2>&1 | tee -aeds.mrp.log

dm/sdp:
	time ../../main.py --score sdp \
	  --read mrp --gold ../sample/psd/wsj.mrp \
	  ../sample/dm/wsj.mrp 2>&1 | tee -adm.sdp.log

peking/sdp:
	time ../../main.py --score sdp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp 2>&1 | tee -apeking.sdp.log

peking/smatch:
	time ../../main.py --score smatch --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp 2>&1 | tee -apeking.smatch.log

peking/mrp:
	time ../../main.py --score mrp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp 2>&1 | tee -apeking.mrp.log

ucca/ucca:
	time ../../main.py --score ucca \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp 2>&1 | tee -aucca.ucca.log

ucca/smatch:
	time ../../main.py --score smatch \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp 2>&1 | tee -aucca.smatch.log
ucca/mrp:
	time ../../main.py --score mrp \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp 2>&1 | tee -aucca.mrp.log

test/smatch:
	time ../../main.py --score smatch --limit 50 \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr 2>&1 | tee -atest.smatch.log

coli/smatch:
	time ../../main.py --score smatch \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr 2>&1 | tee -acoli.smatch.log

coli/mrp:
	time ../../main.py --score mrp \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr 2>&1 | tee -acoli.smatch.log
