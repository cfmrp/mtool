.PHONY: dm/wsj.mrp eds/wsj.mrp psd/wsj.mrp ucca/wsj.mrp \
	amr/pdf dm/pdf eds/pdf psd/pdf ucca/pdf \
	clean release

amr/wsj.mrp: wsj.ids ../wsj.txt amr/wsj.amr
	for i in $$(cat wsj.ids); do \
	  ../../main.py --text ../wsj.txt --read amr \
	    --id $$i --write mrp ./amr/wsj.amr; \
	done > $@;

amr/pdf:
	for i in $$(cat wsj.ids); do \
	../../main.py --text ../wsj.txt --read amr \
	  --id $$i --write dot \
	  ./amr/wsj.amr ./amr/dot/$$i.dot; \
	done
	for i in ./amr/dot/*.dot; do \
	  j=$$(basename $$i .dot); \
	  dot -Tpdf $$i > ./amr/pdf/$${j}.pdf; \
	done

dm/wsj.mrp:
	for i in $$(cat wsj.ids); do \
	  ../../main.py --text ../wsj.txt --read dm \
	    --id $$i --write mrp ./dm/wsj.sdp; \
	done > ./dm/wsj.mrp;

dm/pdf:
	for i in $$(cat wsj.ids); do \
	../../main.py --text ../wsj.txt --read dm \
	  --id $$i --write dot \
	  ./dm/wsj.sdp ./dm/dot/$$i.dot; \
	done
	for i in ./dm/dot/*.dot; do \
	  j=$$(basename $$i .dot); \
	  dot -Tpdf $$i > ./dm/pdf/$${j}.pdf; \
	done

eds/wsj.mrp:
	for i in $$(cat wsj.ids); do \
	  ../../main.py --text ../wsj.txt --read eds \
	    --id $$i --write mrp ./eds/wsj.eds; \
	done > ./eds/wsj.mrp;

eds/pdf:
	for i in $$(cat wsj.ids); do \
	../../main.py --text ../wsj.txt --read eds \
	  --id $$i --write dot \
	  ./eds/wsj.eds ./eds/dot/$$i.dot; \
	done
	for i in ./eds/dot/*.dot; do \
	  j=$$(basename $$i .dot); \
	  dot -Tpdf $$i > ./eds/pdf/$${j}.pdf; \
	done

psd/wsj.mrp:
	for i in $$(cat wsj.ids); do \
	  ../../main.py --text ../wsj.txt --read psd \
	    --id $$i --write mrp ./psd/wsj.sdp; \
	done > ./psd/wsj.mrp;

psd/pdf:
	for i in $$(cat wsj.ids); do \
	../../main.py --text ../wsj.txt --read dm \
	  --id $$i --write dot \
	  ./psd/wsj.sdp ./psd/dot/$$i.dot; \
	done
	for i in ./psd/dot/*.dot; do \
	  j=$$(basename $$i .dot); \
	  dot -Tpdf $$i > ./psd/pdf/$${j}.pdf; \
	done

ucca/wsj.mrp:
	for i in $$(cat wsj.ids); do \
	  ../../main.py --text ../wsj.txt --read ucca \
	    --id $$i --write mrp ./ucca/xml/files.txt; \
	done > ./ucca/wsj.mrp;

ucca/pdf:
	for i in $$(cat wsj.ids); do \
	../../main.py --text ../wsj.txt --read ucca \
	  --id $$i --write dot --strings \
	  ./ucca/xml/files.txt ./ucca/dot/$$i.dot; \
	done
	rm $$(find ./ucca/dot -size 0);
	for i in ./ucca/dot/*.dot; do \
	  j=$$(basename $$i .dot); \
	  dot -Tpdf $$i > ./ucca/pdf/$${j}.pdf; \
	done

clean:
	rm */wsj.mrp

release: 
	tar zpScvf ../public/sample.tgz --transform='s@^@mrp/2019/sample/@'\
	  README.txt Makefile \
	  amr/wsj.mrp dm/wsj.mrp eds/wsj.mrp psd/wsj.mrp ucca/wsj.mrp \
	  amr/dot amr/pdf dm/dot dm/pdf eds/dot eds/pdf \
	  psd/dot psd/pdf ucca/dot ucca/pdf



