.PHONY: history regression

history:
	git log --pretty=tformat:"%H	%ae	%ai	%s" -- score/mces.py

regression:
	[ -d etc ] || mkdir etc; \
	[ -d tmp ] || mkdir tmp; \
	for i in $$(awk '{print $$1}' data/score/revisions.txt); do \
	  [ -d etc/$${i} ] || mkdir etc/$${i}; \
	  ( cd tmp; \
	    [ -d $${i} ] || git clone git@github.com:cfmrp/mtool.git $${i}; \
	    cd $${i}; git checkout $${i}; \
	    cd data/score; sbatch ../../../../data/score/test.slurm; ) \
	done
