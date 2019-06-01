.PHONY: amr edm peking sdp smatch ucca

amr:
	../../main.py --score smatch \
	  --read amr --gold test1.amr \
	  test2.amr

edm:
	../../main.py --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/dm/wsj.mrp

eds:
	../../main.py --score smatch \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/amr/wsj.mrp

peking:
	../../main.py --score sdp \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm peking.wsj.dm.sdp

sdp:
	../../main.py --score sdp \
	  --read mrp --gold ../sample/psd/wsj.mrp \
	  ../sample/dm/wsj.mrp

ucca:
	../../main.py --score ucca \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp
