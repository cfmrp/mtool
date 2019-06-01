.PHONY: edm pet peking sdp smatch ucca

edm:
	../../main.py --score edm \
	  --read mrp --gold ../sample/eds/wsj.mrp \
	  ../sample/dm/wsj.mrp

pet:
	../../main.py --score edm \
	  --format mrp --gold ../sample/eds/wsj.mrp \
	  --read eds eds/wsj.pet.eds

sdp:
	../../main.py --score sdp \
	  --read mrp --gold ../sample/psd/wsj.mrp \
	  ../sample/dm/wsj.mrp

peking:
	../../main.py --score sdp --text ../wsj.txt \
	  --format dm --gold ../../../evaluation/dm/wsj.sdp \
	  --read dm dm/peking.wsj.sdp

smatch:
	../../main.py --score smatch \
	  --read amr --gold amr/test1.amr \
	  amr/test2.amr

ucca:
	../../main.py --score ucca \
	  --read mrp --gold ucca/ewt.gold.mrp \
	  ucca/ewt.tupa.mrp
