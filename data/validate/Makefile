.PHONY: all

all:
	time python3 -u ../../main.py --trace --trace --validate all \
	  --read mrp eds/wsj.mrp $@ 2>&1 | tee eds.wsj.log
